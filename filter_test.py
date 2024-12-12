class YesNo(BaseModel):
  yes_or_no_code: Literal['yes', 'no']
  code_snippet: str | None



ollama.pull('llama3')

all_doc_with_code = []
for doc in documents:
    one_response = []
    hasCode = False
    for response in doc:
        extract_code_prompt = f"Does the passage of text involve a coding question? If yes, extract all the Python code snippets found in this passage of text. The code should be extracted in its original form, without any modifications or transformations and with no commentary. If there is no code, return nothing. If there is code, return the code snippet.\n{response}"
        find_student_question = f"You are reading an email exchanged between a student and a professor. Identify whether the email is from a student who is stuck on a problem, or the professor offering a solution. If it is a student, explain clearly what problem the student is stuck on. Explain the context of the problem and what specific concepts the student is struggling on. If there is no question or problem the student has, return nothing. If it is the professor, explain clearly the solution offered by the professor. Explain the context of the solution and rationale. \n{response}"
        # generate a response combining the prompt and data we retrieved in step 2
        output = ollama.generate(
            model="llama3",
            prompt=extract_code_prompt,
            format=YesNo.model_json_schema()
        )
        outdict = ast.literal_eval(output['response'].replace('null', 'None').strip())

        if outdict['yes_or_no_code'] == 'yes':
            hasCode = True
            output2 = ollama.generate(
                model="llama3",
                prompt=find_student_question
            )
        one_response.append({'question_or_answer': output, 'code_snippet': outdict['code_snippet']})

    if hasCode:
        all_doc_with_code.append(one_response)
        for one in one_response:
            for key, value in one.items():
                print(value)
                print("\n")
        print('done\n\n')
