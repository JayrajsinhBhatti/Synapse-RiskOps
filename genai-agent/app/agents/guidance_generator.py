"""
genai-agent/app/agents/guidance_generator.py
Owner: Person 1 | Week: 3 (initial) -> Week 4 (proactive guidance)

Third agent in the LangGraph RCA pipeline.
- Takes the identified root cause and generates natural-language, step-by-step
  guidance for engineers (or automation) using Gemini
- Week 4: extend to generate *proactive* guidance — preventive steps before a
  predicted failure actually occurs
- Output matches the "guidance" block of shared/schemas/incident_record.schema.json
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash-lite')

prompt = PromptTemplate(
    template="""
You are an experienced Site Reliability Engineer.

Root cause identified:
{root_cause}

Generate practical guidance for the incident.

Return ONLY valid JSON in this format:

{{
    "guidance": {{
        "summary": "",
        "immediate_actions": [
            ""
        ],
        "preventive_measures": [
            ""
        ]
    }}
}}
""",
    input_variables=["root_cause"]
)

parser = JsonOutputParser()

chain = prompt | llm | parser

def guidance_generator(state):
  root_cause = state['root_cause_candidates_ranked'][0]
  
  response = chain.invoke({
    'root_cause': root_cause
  })
  
  return {
    'guidance': response['guidance']
  }