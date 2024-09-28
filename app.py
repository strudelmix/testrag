from fastapi import FastAPI
from transformers import pipeline
import torch

# Create a new FastAPI app instance
app = FastAPI()

email_chain = []
# Initialize the text generation pipeline
# This function will be able to generate text
# given an input.
pipe = pipeline("text-generation",
                model="meta-llama/Meta-Llama-3-8B-Instruct",
                model_kwargs={
                    "torch_dtype": torch.float16,
                    "quantization_config": {"load_in_4bit": True},
                    "low_cpu_mem_usage": True
                    }
                )

terminators = [
    pipeline.tokenizer.eos_token_id,
    pipeline.tokenizer.convert_tokens_to_ids("<|eot_id|>"),
]

def to_one_sen(one_title):
    message = [
                {"role": "system", "content":
                    """
                        You are the steward of a group of chunks which represent groups of email chains that talk about a similar topic
                        A new email chain was just added to one of your chunks, Identify the question, problem, or issue that the email chain is discussing, then you should generate a very brief 1-sentence summary which will inform viewers what a chunk group is about.
            
                        A good summary will say what the chunk is about, and give any clarifying instructions on what to add to the chunk.
            
                        You will be given a group of propositions which are in the chunk and the chunks current summary.
            
                        Your summaries should anticipate generalization. If you get text about apples, generalize it to food.
                        Or month, generalize it to "date and times". 
                        
                        Ignore greetings, signoffs, and names. 
            
                        Example:
                        Input: 
                        Greg M.: Hi Professor, I've been confused on how to call an external command within Python as if I had typed it in a shell or command prompt? I've been trying to rack my head around it. Greg
                        Prof. Kwang: Hi Greg, sorry for the late response. I believe that you can use subprocess.run(["ls", "-l"]. From, Abe Kwang
                        Output: This chunk contains information about calling external commands in Python.
            
                        Only respond with the new chunk summary, nothing else.
                        """
                },
                {"role": "user", "content": one_title}
            ]

    one_sen = pipe(message,
                 max_new_tokens=256,
                 eos_token_id=terminators,
                 do_sample=True,
                 temperature=0.6,
                 top_p=0.9,
                 )

    return one_sen[0]["generated_text"][-1]["content"]


def to_title(sen_sum):
    message = [
        {"role": "system", "content":
        """
            You are the steward of a group of chunks which represent groups of email chains that talk about a similar topic
            A new email chain was just added to one of your chunks, Identify the question, problem, or issue that the email chain is discussing, then you should generate a very brief 1-sentence summary which will inform viewers what a chunk group is about.

            A good summary will say what the chunk is about, and give any clarifying instructions on what to add to the chunk.

            You will be given a group of propositions which are in the chunk and the chunks current summary.

            Your summaries should anticipate generalization. If you get text about apples, generalize it to food.
            Or month, generalize it to "date and times". 

            Ignore greetings, signoffs, and names. 

            Example:
            Input: 
            Greg M.: Hi Professor, I've been confused on how to call an external command within Python as if I had typed it in a shell or command prompt? I've been trying to rack my head around it. Greg
            Prof. Kwang: Hi Greg, sorry for the late response. I believe that you can use subprocess.run(["ls", "-l"]. From, Abe Kwang
            Output: This chunk contains information about calling external commands in Python.

            Only respond with the new chunk summary, nothing else.
            """
        },
        {"role": "user", "content": sen_sum}
    ]

    title = pipe(message,
        max_new_tokens=256,
        eos_token_id=terminators,
        do_sample=True,
        temperature=0.6,
        top_p=0.9,
    )

    return title[0]["generated_text"][-1]["content"]


# Define a function to handle the GET request at `/generate`
# The generate() function is defined as a FastAPI route that takes a
# string parameter called text. The function generates text based on the # input using the pipeline() object, and returns a JSON response
# containing the generated text under the key "output"
@app.get("/generate")
def generate(): # text: str
    # Use the pipeline to generate text from the given input text

    one_sen = to_one_sen(email_chain)
    title = to_title(one_sen)
    # Return the generated text in a JSON response
    return {"output": title}
