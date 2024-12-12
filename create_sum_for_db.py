import chromadb
import ollama
import json
from pydantic import BaseModel
from typing import Literal
import ast

client = chromadb.Client()
collection = client.create_collection(name="docs")

input_vector_doc = []
with open("sent_mail_2.json", "r") as outfile:
    documents = json.load(outfile)

for dia in documents:
    one_input = ""
    for response in dia:
        response = response.replace("show quoted text", "")
        one_input = one_input + response + "\n"
    input_vector_doc.append(one_input)
print("created filtered docs")
"""
ollama.pull('mxbai-embed-large')
print('pulled embeddings')
ollama.pull('codellama')
print("pulled llama")
# store each document in a vector embedding database
for i, d in enumerate(input_vector_doc):
    response = ollama.embeddings(model="mxbai-embed-large", prompt=d)
    print('response done')
    embedding = response["embedding"]
    print('embedding done')
    collection.add(
        ids=[str(i)],
        embeddings=[embedding],
        documents=[d]
    )
    print('collection added')
print('all enumerated')

student_question = """      "Student:           \nSubject: Implement regression trees - CART\n\nPlease find the below implementation I am missing something in the below statement I believe I have to pass yTr index corresponding to that feature\nRequesting you to assist me on this\nleft_inds=index[xTr[:feature]<=cut]\n      right_inds=index[xTr[:feature]>cut]\nDef cart(xTr yTr):\n  # YOUR CODE HERE\n  index=nparange(d)\n  depth=0\n  result1 = npall(yTr == yTr[0])\n  result2 = npmax(npabs(npdiff(xTraxis=0))) < (npfinfo(float)eps * 100)\n  #npall(xTr == xTr[0])\n  print(\"result1\"result1)\n  print(\"result2\"result2)\n  pred = npmean(yTr)\n  if(result1 or result2):\n       tree = TreeNode(NoneNoneNoneNonepred)\n  else:\n      depth=depth+1\n      feature cut loss = sqsplit(xTr yTr)\n      #i=indexes[yTr]\n      left_inds=index[xTr[:feature]<=cut]\n      right_inds=index[xTr[:feature]>cut]\n      left_child=cart(xTr[left_inds]yTr[left_inds])\n      right_child=cart(xTr[right_inds]yTr[right_inds])\n      tree = TreeNode(left_child right_child feature cut pred)\n  return tree\n","""
# an example prompt

# generate an embedding for the prompt and retrieve the most relevant doc
response = ollama.embeddings(
    prompt=student_question,
    model="mxbai-embed-large"
)
print('res generated')

# cosine similarity
results = collection.query(
    query_embeddings=[response["embedding"]],
    n_results=1
)
data = results['documents'][0][0]
"""

"""
extract_code_prompt = f"You are an helpful AI assisting a machine learning engineer with prompt generation. Generate a prompt that can be fed into a model to extract Python code from unstructured text."
output = ollama.generate(
    model="llama2",
    prompt=extract_code_prompt
)

print(output['response'])
exit()
"""

code_q = []
# email_summary_prompter = f"You are a renowned chatbot assistant aiding in solving customer support tickets. A customer currently has a question which is labeled as '## Question:'. Outlined below are previously completed customer support tickets labeled '## Ticket 1:', '## Ticket 2:', and so forth. For each ticket, describe the question that the customer has, and the successful solution that solved the issue. Explain how and why this solution solved the problem, and thoroughly breakdown your rationale. Then, answer the question that the current customer has. It is crucial to your wellbeing that you only respond with factual information. If you do not understand why and how a solution solved the customer problem, do not attempt to explain the solution.\n\n## Question:\n{student_question}\n\n"
# email_summary_prompter = f"You are a renowned chatbot assistant aiding in solving student questions. A student currently has a question which is labeled as '## Question:'. You are given a previously completed student problem labeled as '## Ticket:'. The ticket is in a dialogue format between 'Student:' and 'Professor:'. Edit the code that the student has a question about to provide a successful solution. It is crucial to your wellbeing that you only respond with factual information. If you do not understand why or how to solve the problem, do not attempt to explain the solution.\n\n## Question:\n{student_question}\n\n##Ticket: {data}"


class YesNo(BaseModel):
  yes_or_no_code: Literal['yes', 'no']
  code_snippet: str | None



ollama.pull('llama3')

all_doc_with_code = []
for doc in documents:
    one_response = []
    hasCode = False
    save_code = {}
    save_outer_dict = {}
    counter1 = 0
    for response in doc:
        extract_code_prompt = f"Does the passage of text involve a coding question? If yes, extract all the Python code snippets found in this passage of text. The code should be extracted in its original form, without any modifications or transformations and with no commentary. If there is no code, return nothing. If there is code, return the code snippet.\n{response}"
        # generate a response combining the prompt and data we retrieved in step 2
        output = ollama.generate(
            model="llama3",
            prompt=extract_code_prompt,
            format=YesNo.model_json_schema()
        )
        outdict = ast.literal_eval(output['response'].replace('null', 'None').strip())

        if outdict['yes_or_no_code'] == 'yes':
            hasCode = True
            save_code.update({counter1: outdict['code_snippet']})
        counter1 += 1
        one_response.append(response)

    if hasCode:
        save_list = []
        list_counters = sorted(list(save_code.keys()))

        current_code = save_code[list_counters[0]]
        counter2 = 0

        for response in one_response:
            if counter2 + 1 < len(list_counters):
                if one_response.index(response) == list_counters[counter2 + 1]:
                    counter2 += 1
                    current_code = save_code[list_counters[counter2]]

            find_student_question = f"You are reading an email exchanged between a student and a professor on machine learning. Identify whether the email is from a student who is stuck on a problem, or the professor offering a solution. If it is a student, explain clearly what problem the student is stuck on. Explain the context of the problem and what specific concepts the student is struggling on. If there is no question or problem the student has, return nothing. To aid your answer if it is an email from a student, the code snippet the student is struggling on is given, If it is the professor, explain clearly the solution offered by the professor. Explain the context of the solution and rationale. To aid your answer, if the email is from the professor offering a solution, the modified code snippet from the professor is provided.\n{response}\n<code>\n{current_code}\n</code>"

            output2 = ollama.generate(
                model="llama3",
                prompt=find_student_question
            )
            save_list.append(output2['response'])

        save_outer_dict.update({'question_or_answer': save_list, 'code_snippet': save_code})
        print(save_list)
        print("\n")
        print(save_code)
        print('done\n\n')
    all_doc_with_code.append(save_outer_dict)

with open("sent_mail_3.json", "a") as outfile:
    json.dump(all_doc_with_code, outfile, indent=4)

    """
    verify_extract = f"Is the passage of text a code snippet? Answer only yes or no, with no commentary. If 'no' or is empty, return No. \n{to_feed}"
    output3 = ollama.generate(
        model="llama3",
        prompt=verify_extract
    )

    print(output3['response'])
    """




# give the AI a support ticket. it needs to solve it. first, ask it to break down the email chain so that it has a
# quick one sentence summary of the problem. when it is able to give the one sentence problem, then ask it to explain
# what rationale it believes it may require in order to solve the problem. break down the question, step back,
# and ask follow up questions.

# NOTE: agentic chunker has to go back and summarize chunks by problem, solution, and rationale. So edit the file.
# so each chunk has an overview of the general problems in the email chain, the general solutions, and general rationale.

# first organize each retrieved document. by asking an AI agent what the problem was, what the solution is, and the rationale.
# save these values in a dictionary.
# ask the AI to generalize the problem and then find the closest chunk. if no chunk exists, then create a new chunk.

# THEN, it is given a prompt that it needs to solve


"""
message_input = [
  {"role": "system", "content":
    You are a renowned chatbot assistant aiding in solving customer support tickets. You are given a query 
    that consists of dialogue between a customer and a support agent. In each dialogue, the customer wants to 
    solve a problem they are running into and wants the support agent to help them solve it. Identify the 
    problem that the customer is having. Are follow-up questions needed in ordered to solve the issue? If so, 
    generate follow-up questions, their answers, and then the final answer to the customer's problem. 
    Outlined below are previously completed customer support ticket summaries to aid your reasoning, 
    labeled "## Ticket 1", "## Ticket 2", and so forth. Provide rationale for your response. It is crucial to 
    your wellbeing that you only respond with factual information. If you are unable to solve or aid the 
    customer support ticket with the information you are given, say that you cannot provide an answer.
   },
  {"role": "user",
   "content":
     f"## Instruction: {instruction}"
     f"## Ticket #1: {evidence}"
   }
]


def rag_verifier(chunk):
    # extract response and rationale
    class ExtractResRat(BaseModel):
        'Extracting the chunk id'
        response: str
        rationale: str

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
"""

"""
you are given the students code and their question, and the professor's answer.
a student has a question with their code (add code if solution matches). then the professor offers a solution. (add code if solution counter matches) 

"""
