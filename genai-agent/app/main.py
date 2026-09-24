"""genai-agent/app/main.py
Owner: Person 1

FastAPI application entrypoint for the GenAI Agent service.
- Initializes the FastAPI app with OpenTelemetry instrumentation
- Registers routers: /diagnose (RCA + remediation pipeline)
- Wires up the LangGraph StateGraph from app/graph/state_graph.py on startup
- Calls ml-engine's api/graph_traversal.py endpoint for dependency graph queries
- Routes alerts to n8n and Activepieces automation engines
  (see shared/api-contracts.md for the contract)
"""

import os

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.schemas.incident import DiagnoseRequest, DiagnoseResponse
from app.graph.state_graph import pipeline
from app.chatbot.router import router as chatbot_router


app = FastAPI(
    title="Synapse RiskOps - GenAI Agent",
    description=(
        "LangGraph-powered RCA pipeline: "
        "ML prediction → Log analysis → Root cause identification → "
        "Proactive guidance → Confidence-based routing."
    ),
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Initialize OpenTelemetry
try:
    from app.telemetry import init_telemetry
    init_telemetry(app)
except Exception as exc:
    logger.warning(f"OpenTelemetry init failed (non-fatal): {exc}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chatbot_router)

N8N_WEBHOOK_URL = os.getenv(
    "N8N_WEBHOOK_URL",
    "http://n8n:5678/webhook/alert",
)

ACTIVEPIECES_WEBHOOK_URL = os.getenv(
    "ACTIVEPIECES_WEBHOOK_URL",
    "http://activepieces:80/api/v1/webhooks",
)


@app.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(request: DiagnoseRequest):
    """
    Run the full RCA pipeline for a service.

    1. ml_node         — calls ml-engine POST /api/risk-score + GET /api/graph/traverse
    2. log_analyzer    — extracts signal from the supplied log entries
    3. root_cause_identifier — ranks root cause candidates (Gemini + dependency graph)
    4. proactive_guidance_generator — generates preventive guidance (Gemini)
    5. confidence_router — decides auto_remediate vs escalate

    Returns a DiagnoseResponse that maps to shared/schemas/incident_record.schema.json.
    """
    initial_state = {
        "metrics": request.metrics.model_dump(),
        "logs": request.logs,
    }

    try:
        result = pipeline.invoke(initial_state)
    except Exception as exc:
        logger.error(f"Pipeline failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}")

    response = DiagnoseResponse(
        service_name=request.metrics.service_name,
        risk_score=result.get("risk_score", 0),
        risk_tier=result.get("risk_tier", "unknown"),
        prediction_confidence=result.get("prediction_confidence", 0),
        predicted_failure_type=result.get("predicted_failure_type", "none"),
        prediction_horizon_minutes=result.get("prediction_horizon_minutes", 0),
        root_cause_candidates_ranked=result.get(
            "root_cause_candidates_ranked", []
        ),
        guidance=result.get("guidance"),
        routing_decision=result.get("routing_decision", "escalate"),
        routing_reason=result.get("routing_reason", ""),
        remediation_result=result.get("remediation_result"),
    )

    # Send the diagnosis and routing decision to n8n + Activepieces
    payload = response.model_dump()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # n8n webhook
            await client.post(N8N_WEBHOOK_URL, json=payload)
            logger.info(
                f"Sent routing decision to n8n: {response.routing_decision}"
            )

            # Activepieces webhook (for ticket creation / notifications)
            try:
                await client.post(ACTIVEPIECES_WEBHOOK_URL, json=payload)
                logger.info("Sent event to Activepieces")
            except Exception as ap_exc:
                logger.warning(f"Activepieces webhook failed (non-fatal): {ap_exc}")

    except Exception as exc:
        # Automation failure should not make the diagnosis itself fail
        logger.warning(f"Failed to send alert to automation: {exc}")

    return response


@app.get("/health", tags=["System"])
async def health():
    """Health check used by Docker and load balancers."""
    return {
        "status": "healthy",
        "service": "genai-agent",
        "version": "0.3.0",
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "service": "Synapse RiskOps - GenAI Agent",
        "version": "0.3.0",
        "docs": "/docs",
        "endpoints": {
            "diagnose": "POST /diagnose",
            "health": "GET /health",
        },
    }