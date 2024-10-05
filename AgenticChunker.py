from transformers import pipeline
import torch
from typing import Optional
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.chains import create_extraction_chain_pydantic
import instructor
import uuid
from openai import OpenAI

email_chain = []


# Initialize the text generation pipeline
# This function will be able to generate text
# given an input.

class AgenticChunker:
    def __init__(self, api_key=None):
        self.chunks = {}
        # no long IDs created
        self.id_truncate_limit = 5

        # Update summaries
        self.generate_new_metadata = True
        self.print_logging = True

        if api_key is None:
            raise ValueError("No API Key provided")

        self.model_name = "meta-llama/Meta-Llama-3-8B-Instruct"

        # gets Llama model for inference mode
        # self.pipe = pipeline("text-generation",
        #                model="meta-llama/Meta-Llama-3-8B-Instruct",
        #                model_kwargs={
        #                    "torch_dtype": torch.float16,
        #                    "quantization_config": {"load_in_4bit": True},
        #                    "low_cpu_mem_usage": True
        #                    }
        #                )

        self.terminators = [
            pipeline.tokenizer.eos_token_id,
            pipeline.tokenizer.convert_tokens_to_ids("<|eot_id|>"),
        ]

    # collect the list of emails in variable email_chain
    def add_email_chains(self, email_chains):
        for email_chain in email_chains:
            self.add_email_chain(email_chain)

    def add_email_chain(self, email_chain):
        if self.print_logging:
            print(f"\nAdding: '{email_chain}'")

        if len(self.chunks) == 0:
            if self.print_logging:
                print("No chunks, creating new chunk")
            # if no chunks are in the dictionary chunks, create a new one
            self._create_new_chunk(email_chain)
            return

        # if chunks were already created, then look for the one relevant to the email
        chunk_id = self._find_relevant_chunk(email_chain)

        if chunk_id:
            if self.print_logging:
                print(f"Chunk Found ({self.chunks[chunk_id]['chunk_id']}), adding to: {self.chunks[chunk_id]['title']}")
            self.add_email_chain_to_chunk(chunk_id, email_chain)
            return
        else:
            if self.print_logging:
                print("No chunks found")
            self._create_new_chunk(email_chain)

    def _create_new_chunk(self, email_chain):
        # This line of code generates a new unique identifier (UUID) and truncates it to a specified length. UUIDs
        # are 128-bit numbers used to uniquely identify information in computer systems. The uuid4 method creates a
        # random UUID.

        # [:self.id_truncate_limit]: This slices the string representation of the UUID to take only the first
        # self.id_truncate_limit characters. This is done to ensure that the resulting ID is not excessively long.

        new_chunk_id = str(uuid.uuid4())[:self.id_truncate_limit]  # I don't want long ids
        new_chunk_summary = self._create_new_chunk_summary(email_chain)
        new_chunk_title = self._create_new_chunk_title(new_chunk_summary)

        self.chunks[new_chunk_id] = {
            'chunk_id': new_chunk_id,
            'email_chains': [email_chain],
            'title': new_chunk_title,
            'summary': new_chunk_summary,
            'chunk_index': len(self.chunks)
        }
        if self.print_logging:
            print(f"Created new chunk ({new_chunk_id}): {new_chunk_title}")

    def _create_new_chunk_summary(self, email_chain):
        message_input = [
            {"role": "system", "content":
                """
                    You are the steward of a group of chunks which represent groups of email chains that talk about a similar topic
                    You should generate a very brief 1-sentence summary which will inform viewers what a chunk group is about.

                    A good summary will say what the chunk is about, and give any clarifying instructions on what to add to the chunk.

                    You will be given an email chain which will go into a new chunk. This new chunk needs a summary.

                    Your summaries should anticipate generalization. If you get an email chain about apples, generalize it to food.
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
            {"role": "user",
             "content": f"Determine the summary of the new chunk that this email chain will go into:\n{email_chain}"}
        ]

        # Pydantic data class
        class ChunkSummary(BaseModel):
            chunk_id: str

        client = instructor.from_openai(
            OpenAI(
                base_url="http://localhost:11434/v1",
                api_key="ollama",  # required, but unused
            ),
            mode=instructor.Mode.JSON,
        )

        resp = client.chat.completions.create(
            model="llama3",
            message=message_input,
            response_model=ChunkSummary,
        )

        # this is the summary
        return resp.model_dump_json

    def _create_new_chunk_title(self, summary):
        message_input = [
            {"role": "system", "content":
                """
                    You are the steward of a group of chunks which represent groups of sentences that talk about a similar topic
                    You should generate a very brief few word chunk title which will inform viewers what a chunk group is about.

                    A good chunk title is brief but encompasses what the chunk is about

                    You will be given a summary of a chunk which needs a title

                    Your titles should anticipate generalization. If you get a proposition about apples, generalize it to food.
                    Or month, generalize it to "date and times".

                    Example:
                    Input: Summary: This chunk is about dates and times
                    Output: Date & Times

                    Only respond with the new chunk title, nothing else.

                    """
             },
            {"role": "user", "content": f"Determine the title of the chunk that this summary belongs to:\n{summary}"}
        ]

        # Pydantic data class
        class ChunkTitle(BaseModel):
            chunk_id: str

        client = instructor.from_openai(
            OpenAI(
                base_url="http://localhost:11434/v1",
                api_key="ollama",  # required, but unused
            ),
            mode=instructor.Mode.JSON,
        )

        resp = client.chat.completions.create(
            model="llama3",
            message=message_input,
            response_model=ChunkTitle,
        )

        # this is the summary
        return resp.model_dump_json

    # you received an email that you need to find the relevant chunk for
    def _find_relevant_chunk(self, email_chain):
        current_chunk_outline = self.get_chunk_outline()

        message_input = [
            {"role": "system", "content":
                """
                    Determine whether or not the "Email chain" should belong to any of the existing chunks.

                    An email chain should belong to a chunk of their initial question, solution, or issues that are similar.
                    The goal is to group similar email chains and chunks.

                    If you think an email chain should be joined with a chunk, return the chunk id.
                    If you do not think an item should be joined with an existing chunk, just return "No chunks"

                    Ignore greetings, signoffs, and names. 

                    Example:
                    Input: 
                        - Email chain: 
                            "Hi, I'm having an issue getting my computer to connect to my router. Please help. Matthew"
                            "Hi Matthew, sorry to hear that. Have you tried turning your PC on and off again? Regards, Andrea"
                            "That worked, thank you so much."
                        - Current Chunks:
                            - Chunk ID: 2n4l3d
                            - Chunk Name: Wifi Connectivity 
                            - Chunk Summary: This chunk contains information about wifi connectivity.

                            - Chunk ID: 93833k
                            - Chunk Name: External Commands in Python 
                            - Chunk Summary: This chunk contains information about calling external commands in Python.
                    Output: 2n4l3d
                    """
             },
            {"role": "user",
             "content": f"Current Chunks:\n--Start of current chunks--\n{current_chunk_outline}\n--End of current chunks--"
                        f"Determine if the following statement should belong to one of the chunks outlined:\n{email_chain}"
             }
        ]

        # define class for getting chunk id
        # Pydantic data class
        class ChunkID(BaseModel):
            """Extracting the chunk id"""
            chunk_id: Optional[str]

        client = instructor.from_openai(
            OpenAI(
                base_url="http://localhost:11434/v1",
                api_key="ollama",  # required, but unused
            ),
            mode=instructor.Mode.JSON,
        )

        resp = client.chat.completions.create(
            model="llama3",
            message=message_input,
            response_model=ChunkID,
        )

        # if bad response or returned nothing
        if resp.model_dump_json != self.id_truncate_limit:
            return None

        # this is the structured chunk id
        return resp.model_dump_json

    def add_email_chain_to_chunk(self, chunk_id, email_chain):
        self.chunks[chunk_id]['email_chains'].append(email_chain)

        if self.generate_new_metadata_ind:
            self.chunks[chunk_id]['summary'] = self._update_chunk_summary(self.chunks[chunk_id])
            self.chunks[chunk_id]['title'] = self._update_chunk_title(self.chunks[chunk_id])

    # chunk is a dict
    def _update_chunk_summary(self, chunk):

        current_summary = chunk['summary']
        # update the summary so it doesn't get stale
        message_input = [
            {"role": "system", "content":
                """
                    You are the steward of a group of chunks which represent groups of email chains that talk about a similar topic
                    A new email chain was just added to one of your chunks, Identify the question, problem, or issue that the email chain is discussing, then you should generate a very brief 1-sentence summary which will inform viewers what a chunk group is about.

                    A good summary will say what the chunk is about, and give any clarifying instructions on what to add to the chunk.

                    You will be given a group of email chains which are in the chunk and the chunks current summary.

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
            {"role": "user",
             "content": f"Chunk's propositions:\n{email_chain}\n\nCurrent chunk summary:\n{current_summary}"}
        ]

        # define class for getting chunk id
        # Pydantic data class
        class ChunkSummary(BaseModel):
            """Extracting the chunk id"""
            chunk_id: str

        client = instructor.from_openai(
            OpenAI(
                base_url="http://localhost:11434/v1",
                api_key="ollama",  # required, but unused
            ),
            mode=instructor.Mode.JSON,
        )

        resp = client.chat.completions.create(
            model="llama3",
            message=message_input,
            response_model=ChunkSummary,
        )

        return resp.model_dump_json

    def _update_chunk_title(self, chunk):

        current_summary = chunk['title']
        # update the summary so it doesn't get stale
        message_input = [
            {"role": "system", "content":
                """
                    You are the steward of a group of chunks which represent groups of email chains that talk about a similar topic
                    A new email chain was just added to one of your chunks, You should generate a very brief updated chunk title which will inform viewers what a chunk group is about.

                    A good title will say what the chunk is about.

                    You will be given a group of email chains which are in the chunk, chunk summary and the chunk title.

                    Your title should anticipate generalization. If you get an email chain about apples, generalize it to food.
                    Or month, generalize it to "date and times".

                    Ignore greetings, signoffs, and names. 

                    Example:
                    Input: This chunk contains information about calling external commands in Python.
                    Output: Python Commands

                    Only respond with the new chunk title, nothing else.
                    """
             },
            {"role": "user",
             "content": f"Chunk's propositions:\n{email_chain}\n\nCurrent chunk summary:\n{current_summary}"}
        ]

        # define class for getting chunk id
        # Pydantic data class
        class ChunkSummary(BaseModel):
            """Extracting the chunk id"""
            chunk_id: str

        client = instructor.from_openai(
            OpenAI(
                base_url="http://localhost:11434/v1",
                api_key="ollama",  # required, but unused
            ),
            mode=instructor.Mode.JSON,
        )

        resp = client.chat.completions.create(
            model="llama3",
            message=message_input,
            response_model=ChunkSummary,
        )

        return resp.model_dump_json

    def get_chunk_outline(self):
        """
        Get a string which represents the chunks you currently have.
        This will be empty when you first start off
        """
        chunk_outline = ""

        for chunk_id, chunk in self.chunks.items():
            single_chunk_string = f"""Chunk ({chunk['chunk_id']}): {chunk['title']}\nSummary: {chunk['summary']}\n\n"""

            chunk_outline += single_chunk_string

        return chunk_outline

    def get_chunks(self, get_type='dict'):
        """
        This function returns the chunks in the format specified by the 'get_type' parameter.
        If 'get_type' is 'dict', it returns the chunks as a dictionary.
        If 'get_type' is 'list_of_strings', it returns the chunks as a list of strings, where each string is a proposition in the chunk.
        """
        if get_type == 'dict':
            return self.chunks
        if get_type == 'list_of_strings':
            chunks = []
            for chunk_id, chunk in self.chunks.items():
                chunks.append(" ".join([x for x in chunk['email_chains']]))
            return chunks

    def pretty_print_chunks(self):
        print(f"\nYou have {len(self.chunks)} chunks\n")
        for chunk_id, chunk in self.chunks.items():
            print(f"Chunk #{chunk['chunk_index']}")
            print(f"Chunk ID: {chunk_id}")
            print(f"Summary: {chunk['summary']}")
            print(f"Email chains:")
            for prop in chunk['email chains']:
                print(f"    -{prop}")
            print("\n\n")

    def pretty_print_chunk_outline(self):
        print("Chunk Outline\n")
        print(self.get_chunk_outline())


if __name__ == "__main__":
    ac = AgenticChunker()

    ## Comment and uncomment the propositions to your hearts content
    propositions = [
        'The month is October.',
        'The year is 2023.',
        "One of the most important things that I didn't understand about the world as a child was the degree to which the returns for performance are superlinear.",
        'Teachers and coaches implicitly told us that the returns were linear.',
        "I heard a thousand times that 'You get out what you put in.'",
        # 'Teachers and coaches meant well.',
        # "The statement that 'You get out what you put in' is rarely true.",
        # "If your product is only half as good as your competitor's product, you do not get half as many customers.",
        # "You get no customers if your product is only half as good as your competitor's product.",
        # 'You go out of business if you get no customers.',
        # 'The returns for performance are superlinear in business.',
        # 'Some people think the superlinear returns for performance are a flaw of capitalism.',
        # 'Some people think that changing the rules of capitalism would stop the superlinear returns for performance from being true.',
        # 'Superlinear returns for performance are a feature of the world.',
        # 'Superlinear returns for performance are not an artifact of rules that humans have invented.',
        # 'The same pattern of superlinear returns is observed in fame.',
        # 'The same pattern of superlinear returns is observed in power.',
        # 'The same pattern of superlinear returns is observed in military victories.',
        # 'The same pattern of superlinear returns is observed in knowledge.',
        # 'The same pattern of superlinear returns is observed in benefit to humanity.',
        # 'In fame, power, military victories, knowledge, and benefit to humanity, the rich get richer.'
    ]

    ac.add_email_chains(propositions)
    ac.pretty_print_chunks()
    ac.pretty_print_chunk_outline()
    print(ac.get_chunks(get_type='list_of_strings'))
