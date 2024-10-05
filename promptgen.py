import openai
import instructor
from pydantic import BaseModel
from typing import Iterable


class Album(BaseModel):
    name: str
    artist: str
    year: int


class Response(BaseModel):
    poem: str

class RephraseRespond(BaseModel):
    rephrased_question: str
    answer: str



client = instructor.from_openai(openai.OpenAI())

class FollowUp(BaseModel):
    question: str = Field(description="The follow-up question")
    answer: str = Field(description="The answer to the follow-up question")


class FollowUp(BaseModel):
    follow_ups_required: bool
    follow_ups: list[FollowUp]
    final_answer: str


def self_ask(query):
    return client.chat.completions.create(
        model="gpt-4o",
        response_model=Response,
        messages=[
            {
                "role": "system",
                "content": f"""Query: {query}
                        Are follow-up questions needed?
                        If so, generate follow-up questions, their answers, and then the final answer to the query.
                        """,  # !
            },
        ],
    )


def rephrase_and_respond(query):
    return client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": f"""{query}\nRephrase and expand the question, and respond.""",
            }
        ],
        response_model=Response,
    )


def emotion_prompting(query, stimuli):
    return client.chat.completions.create(
        model="gpt-4o",
        response_model=Iterable[Album],
        messages=[
            {
                "role": "user",
                "content": f"""
                {query}
                {stimuli}
                """,
            }
        ],
    )

def role_prompting(query, role):
    return client.chat.completions.create(
        model="gpt-4o",
        response_model=Response,
        messages=[
            {
                "role": "system",
                "content": f"{role} {query}",
            },
        ],
    )

def reread(query, thinking_prompt):
    return client.chat.completions.create(
        model="gpt-4o",
        response_model=Response,
        messages=[
            {
                "role": "system",
                "content": f"Read the question again: {query} {thinking_prompt}",
            },
        ],
    )

class RelevantProblem(BaseModel):
    problem_explanation: str
    solution: str


class Response(BaseModel):
    relevant_problems: list[RelevantProblem] = Field(
        max_length=3,
        min_length=3,
    )
    answer: RelevantProblem
def analogical_prompting(query: str):
    return client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": dedent(
                    f"""
                <problem>
                {query}
                </problem>

                Relevant Problems: Recall three relevant and
                distinct problems. For each problem, describe
                it and explain the solution before solving
                the problem
                """
                ),
            }
        ],
        model="gpt-4o",
        response_model=Response,
    )



if __name__ == "__main__":
    query = ""
    stimuli = "Finding a solution to the given problem is very important to my career."
    role = "You are a renowned software engineer."
    thinking_prompt = "Let's think step by step."


    em_prompt = False
    role_prompt = True
    think_prompt = False
    follow_prompt = False
    analog_prompt = False

    if em_prompt:
        albums = emotion_prompting(query, stimuli)

        for album in albums:
            print(album)
            #> name='Kid A' artist='Radiohead' year=2000
            #> name='The Marshall Mathers LP' artist='Eminem' year=2000
            #> name='The College Dropout' artist='Kanye West' year=2004
    elif role_prompt:
        response = role_prompting(query, role)
        print(response.poem)
        """
        In the morning's gentle light,
        A brew of warmth, dark and bright.
        Awakening dreams, so sweet,
        In every sip, the day we greet.

        Through the steam, stories spin,
        A liquid muse, caffeine within.
        Moments pause, thoughts unfold,
        In coffee's embrace, we find our gold.
        """
    elif think_prompt:
        query = """Roger has 5 tennis balls.
            He buys 2 more cans of tennis balls.
            Each can has 3 tennis balls.
            How many tennis balls does he have now?
            """
        thinking_prompt = "Let's think step by step."

        response = reread(query=query, thinking_prompt=thinking_prompt)
        print(response.answer)
        # > 11
    elif follow_prompt:
        query = "Who was president of the U.S. when superconductivity was discovered?"

        response = self_ask(query)

        print(response.follow_ups_required)
        # > True
        for follow_up in response.follow_ups:
            print(follow_up)
            """
            question='When was superconductivity discovered?' answer='Superconductivity was discovered in April 1911.'
            """
            """
            question='Who was president of the U.S. in April 1911?' answer='William Howard Taft was the President of the United States in April 1911.'
            """
        print(response.final_answer)
        """
        William Howard Taft was president of the U.S. when superconductivity was discovered.
        """

    elif analog_prompt:
        query = ("What is the area of the square with the four "
                 "vertices at (-2, 2), (2, -2), (-2, -6), and "
                 "(-6, -2)?")
        response = analogical_prompting(query)
        for problem in response.relevant_problems:
            print(problem.model_dump_json(indent=2))
            """
            {
              "problem_explanation": "Determine the distance
              between two points in a coordinate plane.",
              "solution": "To find the distance between two
              points, use the distance formula: \\(d =
              \\sqrt{(x_2 - x_1)^2 + (y_2 - y_1)^2}\\). This
              formula calculates the Euclidean distance between
              points (x_1, y_1) and (x_2, y_2)."
            }
            """
            """
            {
              "problem_explanation": "Calculate the area of a
              square given its side length.",
              "solution": "The area of a square can be found
              using the formula: \\(A = s^2\\), where \\(s\\) is
              the length of one side of the square."
            }
            """
            """
            {
              "problem_explanation": "Identify vertices and
              properties of a geometry shape such as
              parallelogram.",
              "solution": "For any quadrilateral, verify that
              all sides are equal and angles are right angles to
              confirm it is a square. Use properties of
              quadrilaterals and distance formula."
            }
            """

        print(response.answer.model_dump_json(indent=2))
        """
        {
          "problem_explanation": "Calculate the area of a
          square given its vertices.",
          "solution": "First, confirm the shape is a square by
          checking the distance between consecutive vertices
          and ensuring all sides are of equal length using the
          distance formula. For vertices (-2,2), (2,-2),
          (-2,-6), and (-6,-2), calculate distances between
          consecutive points. If distances are equal, use the
          side length to compute area using \\(A = s^2\\)."
        }
        """

