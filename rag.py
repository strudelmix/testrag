import chromadb
import ollama
import json

from langchain.chains.qa_with_sources.retrieval import RetrievalQAWithSourcesChain
from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain_community.llms.ollama import Ollama
from langchain_core.prompts import PromptTemplate
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_qdrant import Qdrant, QdrantVectorStore
from qdrant_client import QdrantClient

from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client.http.models import VectorParams, Distance

ollama.pull('llama3')
ollama.pull('codellama:7b-code')

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,
    chunk_overlap=200,
    length_function = len,
    is_separator_regex = False
)


# codellama_vector = []
input_vector_doc = []
with open("qa_code.json", "r") as outfile:
    documents = json.load(outfile)

for out_dict in documents:
    code_snippet_dict = out_dict['code_snippet']
    code_snippet_dict = {int(key):value for key, value in code_snippet_dict.items()}
    code_keys = [key for key in code_snippet_dict.keys()]
    qa_list = out_dict['question_or_answer']

    qa_code_all = "SUMMARY OF STUDENT AND PROFESSOR EMAILS ON STUDENT PROBLEM WITH CODE SNIPPETS\n"

    counter = 0
    current_code = ''
    for qa in qa_list:
        if counter + 1 < len(code_keys):
            if qa_list.index(qa) == code_keys[counter + 1]:
                counter += 1
                current_code = code_snippet_dict[code_keys[counter]]
                #codellama_splits = text_splitter.split_text(code_snippet_dict[code_keys[counter]])
                #codellama_vector.extend(codellama_splits)
        if current_code != '':
            qa = qa + "\n<code>\n" + current_code + "\n<\code>"

        qa_code_all += qa + "\n"
    qa_code_all += "END OF SUMMARY"
    all_qa_splits = text_splitter.split_text(qa_code_all)
    input_vector_doc.extend(all_qa_splits)



print("loop done")
embeddings = OllamaEmbeddings(model="llama3")
print("llama3 embeddings loaded")
#code_db = FAISS.from_texts(input_vector_doc, embeddings)
# chroma takes FOREVER
# qa_db = Chroma.from_texts(input_vector_doc, embeddings)

# qdrant_db = Qdrant.from_texts(input_vector_doc, embeddings)

client = QdrantClient(":memory:")


#client = QdrantClient(":memory:")
client.create_collection(
    collection_name="demo_collection",
    vectors_config=VectorParams(size=4096, distance=Distance.COSINE)
)


vector_store = QdrantVectorStore(
    client=client,
    collection_name='demo_collection',
    embedding=embeddings
)

print("qa db created")

#code_retriever = code_db.as_retriever(
#    search_type="similarity", search_kwargs={"k": 2},
#)

#qa_retriever = qa_db.as_retriever(
#    search_type="similarity", search_kwargs={"k": 2},
#)
#user_question = "\n  Subject: Code Error in Reduce Variance with Bagging(Project 2)\n\nI got an extension for the submission of my project, and l need some\nassistance debugging my last project.\nFor question one which requires alphas, each time l attempted to multiply\nthe tree with alphas to create prediction, and so l removed it, and only 2\nout of 4 test run passed.\nFor the second question, only two out of three passed, and l am not sure\nwhere the error is because the residual looks okay, but the way it is being\ncalled after the trees and weights are collected is what is still confusing.\nI went through your video, and the pseudo code, and l was able to come up\nwith the current code. Kindly suggest how this could be fixed.\n\nThanks.\n\n"
user_question = "\r\n  Subject: knnclassifier\r\n\r\nThanks\n\r\nI am still not passing the findknn tests. Something is still off with the slicing. The test fails when it tests for \u201ctest=(type(Dg[0][0])==np.float32)\u201d.\r\n\r\nWhat I have now in the findknn code block is this:\r\n\r\ndef findknn(xTr,xTe,k):\r\n    \"\"\"\r\n    function [indices,dists]=findknn(xTr,xTe,k);\r\n\r\n    Finds the k nearest neighbors of xTe in xTr.\r\n\r\n    Input:\r\n    xTr = nxd input matrix with n row-vectors of dimensionality d\r\n    xTe = mxd input matrix with m row-vectors of dimensionality d\r\n    k = number of nearest neighbors to be found\r\n\r\n    Output:\r\n    indices = kxm matrix, where indices(i,j) is the i^th nearest neighbor of xTe(j,:)\r\n    dists = Euclidean distances to the respective nearest neighbors\r\n    \"\"\"\r\n\r\n\r\n    D=l2distance(xTe, xTr)\r\n    (m,n) = D.shape\r\n\r\n    ind = np.argsort(D,0)\r\n    dis = np.sort(D,0)\r\n\r\n    indices = ind[start_index_row_inc:end_index_row_exc,start_index_col_inc:end_index_col_exc]\r\n    dists = dis[:k,:]\r\n\r\n\r\n    return indices, dists\r\n\r\nThank you,\r\n\r\n"
retrieved_docs = vector_store.similarity_search(user_question)
print(user_question)

print("retriever created")
code_llm = Ollama(model="codellama")
print("codellama loaded")

prompt_RAG = """
    You are a renowned professor in machine learning. Your student is asking for help on a machine learning code related question in Python. Respond with the syntactically correct code that solves the problem that the student is having. Make sure you follow these rules:
    1. Use context to understand the code snippets.
    2. Ensure all the requirements in the question are met.
    3. Ensure the output code syntax is correct.
    Below you are also given previous student inquiries on the same or similar question, as well as the code snippet they gave and potentially your response code snippet that solved their issue. After resolving the issue and providing your solution, respond with the entire updated code snippet.
    Question:
    {question}
    Context:
    {context}
    Helpful Response:
    """
prompt_RAG_template = PromptTemplate(
    template=prompt_RAG, input_variables=["context", "question"]
)

docs_content = "\n\n".join(doc.page_content for doc in retrieved_docs)

print("rag template prompt created")
messages = prompt_RAG_template.invoke({"question": user_question, "context": docs_content})
response = code_llm.invoke(messages)

print("qa chain created")
print(response)


#qdrant_chain = RetrievalQAWithSourcesChain.from_chain_type(
#    llm=code_llm,
#    chain_type='stuff',
#    max_tokens_limit=2048,
#    return_source_documents=True,
#    retriever=qdrant.as_retriever(
#        search_type="similarity",
#        search_kwargs={'filter': {'group_id': client}}
#    ),
#    reduce_k_below_max_tokens=False,
#    chain_type_kwargs = {"prompt": prompt_RAG_template}
#)



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

    
    verify_extract = f"Is the passage of text a code snippet? Answer only yes or no, with no commentary. If 'no' or is empty, return No. \n{to_feed}"
    output3 = ollama.generate(
        model="llama3",
        prompt=verify_extract
    )

    print(output3['response'])
    




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
