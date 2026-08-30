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
import os

load_dotenv()


prompt = PromptTemplate(
    template="""
You are an experienced Site Reliability Engineer.

Service observations:
{observations}

Dependency Graph:
{dependency_graph}

ML Engine prediction:
- Risk score: {risk_score}
- Predicted failure type: {predicted_failure_type}

Based on the observations, service dependencies, and the ML Engine's prediction,
identify the most likely root causes.

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
            "affected_services":[],
            "reason":""
        }}
    ]
}}
""",
    input_variables=["observations", "dependency_graph", "risk_score", "predicted_failure_type"]
)

llm = ChatGoogleGenerativeAI(model='gemini-2.5-flash-lite')
parser = JsonOutputParser()

chain = prompt | llm | parser

def root_cause_identifier(state):
    observations = state['observations']

    # Use the real dependency graph fetched by ml_node — fall back to mock if absent
    dependency_graph = state.get('dependency_graph') or {}

    risk_score = state.get('risk_score', 'N/A')
    predicted_failure_type = state.get('predicted_failure_type', 'unknown')

    response = chain.invoke({
        'observations': observations,
        'dependency_graph': dependency_graph,
        'risk_score': risk_score,
        'predicted_failure_type': predicted_failure_type,
    })

    return {
        'root_cause_candidates_ranked':
            response['root_cause_candidates_ranked']
    }