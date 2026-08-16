# This agent should take:

# risk score
# predicted failure
# root cause
# root cause confidence
# dependency information

# info regarding the curr architecture

# generator should return something like:

# {
#   "guidance_steps": [
#     "Inspect payment-service database connection utilization immediately.",
#     "Check for abnormal connection growth or stale connections.",
#     "Reduce unnecessary connection churn where identified.",
#     "Increase the database connection pool only if database capacity allows.",
#     "Monitor payment-service latency and connection utilization for the next 10 minutes.",
#     "Escalate if connection utilization continues increasing despite mitigation."
#   ],
#   "guidance_relevance_score": 94,
#   "guidance_relevance_rubric_notes": "The guidance directly addresses the predicted latency degradation through preventive monitoring and mitigation of the identified database connection exhaustion."
# }

# from app.agents.root_cause_identifier import root_cause_identifier
# from ml_node import get_ml_prediction
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")

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

result = chain.invoke({
    "service": "order-service",
    "risk_score": 0.87,
    "predicted_failure_type": "latency_degradation",
    "prediction_horizon_minutes": 15,
    "root_cause_service": "payment-service",
    "root_cause": "database connection exhaustion",
    "rca_confidence": 0.91,
    "propagation_path": [
        "payment-service",
        "order-service"
    ],
    "logs": [
        "Database connection pool utilization reached 92%",
        "Payment service latency increased by 38%"
    ]
})

print(result)