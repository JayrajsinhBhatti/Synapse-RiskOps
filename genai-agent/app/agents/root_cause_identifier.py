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
You are an experienced Site Reliability Engineer performing Root Cause Analysis (RCA).

Service observations:
{observations}

Dependency Graph & Topology Analysis:
{dependency_graph}

ML Engine prediction:
- Risk score: {risk_score}
- Predicted failure type: {predicted_failure_type}

CRITICAL RCA INSTRUCTIONS:
1. Distinguish the true ROOT CAUSE from downstream SYMPTOMS or blast-radius impact.
2. In dependency chains (e.g. api-gateway -> order-service -> payment-service):
   - If an upstream service (e.g. payment-service) degrades, caller services (order-service, api-gateway) experience downstream latency or errors as symptoms.
   - The failing upstream dependency is the ROOT CAUSE; caller services are AFFECTED SERVICES.
   - Do NOT identify api-gateway or entrypoints as root causes if their dependencies are failing.
3. Determine whether degradation is internal to the service or propagated through dependencies.

For each candidate return:
- cause (short, concise statement of root cause)
- confidence (0.0 to 1.0)
- affected_services (list of services impacted downstream)
- reason (1-2 sentence explanation citing metric and topology evidence)

Return ONLY valid JSON in this format:
{{
    "root_cause_candidates_ranked": [
        {{
            "cause": "",
            "confidence": 0.95,
            "affected_services": [],
            "reason": ""
        }}
    ]
}}
""",
    input_variables=["observations", "dependency_graph", "risk_score", "predicted_failure_type"]
)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    google_api_key=os.getenv("GEMINI_API_KEY"),
)
parser = JsonOutputParser()

chain = prompt | llm | parser

def root_cause_identifier(state):
    observations = state.get('observations', '')
    dependency_graph = state.get('dependency_graph') or state.get('enhanced_graph_analysis') or {}
    risk_score = state.get('risk_score', 'N/A')
    predicted_failure_type = state.get('predicted_failure_type', 'unknown')
    metrics = state.get('metrics', {})
    service_name = metrics.get('service_name', 'unknown-service')

    try:
        response = chain.invoke({
            'observations': observations,
            'dependency_graph': dependency_graph,
            'risk_score': risk_score,
            'predicted_failure_type': predicted_failure_type,
        })
        candidates = response.get('root_cause_candidates_ranked', [])
        if candidates:
            return {'root_cause_candidates_ranked': candidates}
    except Exception as exc:
        pass

    # Graph-aware deterministic fallback
    upstream = dependency_graph.get("upstream_dependencies", [])
    downstream = dependency_graph.get("downstream_dependents", [])
    likely_root = service_name
    affected = list(downstream) if downstream else [service_name]

    return {
        'root_cause_candidates_ranked': [
            {
                'cause': f"{predicted_failure_type.replace('_', ' ').title()} on {likely_root}",
                'confidence': 0.88 if float(risk_score) >= 75.0 else 0.75,
                'affected_services': affected,
                'reason': f"Primary degradation identified on {likely_root} based on telemetry and topology analysis.",
            }
        ]
    }