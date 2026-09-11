# This agent takes:
#
# risk score
# predicted failure
# prediction horizon
# root cause
# root cause confidence
# dependency information (propagation path)
# logs

# and returns:
#
# {
#   "guidance_steps": [
#     "Inspect payment-service database connection utilization immediately.",
#     "Check for abnormal connection growth or stale connections.",
#     ...
#   ],
#   "guidance_relevance_score": 94,
#   "guidance_relevance_rubric_notes": "..."
# }

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    google_api_key=os.getenv("GEMINI_API_KEY"),
)

# output schema
class ProactiveGuidance(BaseModel):
    guidance_steps: list[str] = Field(
        description="Preventive actions to take before the predicted failure occurs"
    )
    guidance_relevance_score: int = Field(
        description="How relevant and actionable the generated guidance is, from 0 to 100"
    )
    guidance_relevance_rubric_notes: str = Field(
        description="Brief explanation of why the guidance is relevant"
    )

prompt = ChatPromptTemplate.from_messages([
    (
    "system",
    """
    You are a production SRE proactive guidance agent.

The system has predicted a failure that has NOT necessarily
happened yet.

Generate preventive actions that engineers can take NOW
to reduce the probability or impact of the predicted failure.

Focus on:
- predicted failure
- identified root cause
- prediction horizon
- affected service
- dependency propagation

Do not give generic recovery instructions.
Do not invent infrastructure facts.
Avoid destructive or irreversible actions.
"""
    ),
    (
        "human",
        """
Service: {service}

Risk score: {risk_score}

Predicted failure: {predicted_failure_type}

Prediction horizon: {prediction_horizon_minutes} minutes

Root cause service: {root_cause_service}

Root cause: {root_cause}

RCA confidence: {rca_confidence}

Propagation path: {propagation_path}

Relevant logs:
{logs}
    """
    )
])

structured_llm = llm.with_structured_output(ProactiveGuidance)

chain = prompt | structured_llm


def proactive_guidance_generator(state: dict) -> dict:
    """
    LangGraph node — generates proactive (preventive) guidance using the
    ML Engine's prediction and the RCA agent's ranked root causes.

    Reads from state:
      metrics, risk_score, predicted_failure_type, prediction_horizon_minutes,
      root_cause_candidates_ranked, dependency_graph, logs

    Writes to state:
      guidance (ProactiveGuidance as dict)
    """
    metrics: dict = state.get("metrics", {})
    service = metrics.get("service_name", "unknown")

    risk_score = state.get("risk_score", 0)
    predicted_failure_type = state.get("predicted_failure_type", "unknown")
    prediction_horizon_minutes = state.get("prediction_horizon_minutes", 0)

    candidates = state.get("root_cause_candidates_ranked", [])
    top_candidate = candidates[0] if candidates else {}
    root_cause_service = top_candidate.get("affected_services", [service])[0] if top_candidate else service
    root_cause = top_candidate.get("cause", "unknown")
    rca_confidence = top_candidate.get("confidence", 0)

    dependency_graph = state.get("dependency_graph", {})
    propagation_path = dependency_graph.get("upstream_dependencies", []) or [service]

    logs = state.get("logs", [])
    log_messages = [log.get("message", str(log)) for log in logs]

    result: ProactiveGuidance = chain.invoke({
        "service": service,
        "risk_score": risk_score,
        "predicted_failure_type": predicted_failure_type,
        "prediction_horizon_minutes": prediction_horizon_minutes,
        "root_cause_service": root_cause_service,
        "root_cause": root_cause,
        "rca_confidence": rca_confidence,
        "propagation_path": propagation_path,
        "logs": log_messages,
    })

    return {
        "guidance": {
            "summary": result.guidance_relevance_rubric_notes,
            "immediate_actions": result.guidance_steps,
            "preventive_measures": [],
            "relevance_score": result.guidance_relevance_score,
        }
    }
