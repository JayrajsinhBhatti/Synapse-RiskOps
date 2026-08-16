"""
genai-agent/app/agents/root_cause_identifier.py
Owner: Person 1 | Week: 3

Second agent in the LangGraph RCA pipeline.
- Combines log_analyzer.py's findings with dependency graph traversal
  (from ml-engine's app/api/graph_traversal.py) to identify the most likely root cause
- Produces a ranked list of root-cause candidates with confidence scores
  (matches "root_cause_candidates_ranked" in shared/schemas/incident_record.schema.json)
- Depends on ml-engine's graph API — mock it via app/mocks/ until Week 3 integration
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
from app.mocks.graph_api import get_dependency_graph

load_dotenv()

import os

load_dotenv()

print("GEMINI_API_KEY:", os.getenv("GEMINI_API_KEY"))

prompt = PromptTemplate(
    template="""
You are an experienced Site Reliability Engineer.

Service observations:
{observations}

Dependency Graph:
{dependency_graph}

Based on the observations and service dependencies, identify the most likely root causes.

For each candidate return:

- cause (short, concise)
- confidence (0-1)
- affected_services (list)
- reason (1-2 sentence explanation)

Return ONLY valid JSON in this format:

{{
    "root_cause_candidates_ranked":[
        {{
            "cause":"",
            "confidence":0.95,
            "affected_services":[]
        }}
    ]
}}
""",
    input_variables=["observations", "dependency_graph"]
)

llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash-lite')
parser = JsonOutputParser()

chain = prompt | llm | parser

def root_cause_identifier(state):
    observations = state['observations']
    
    dependency_graph = get_dependency_graph()
    
    response = chain.invoke ({
        'observations': observations,
        'dependency_graph': dependency_graph
    })
    
    return {
        'root_cause_candidates_ranked':
            response['root_cause_candidates_ranked']
    }