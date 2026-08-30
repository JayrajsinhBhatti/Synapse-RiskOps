"""
genai-agent/app/main.py
Owner: Person 1

FastAPI application entrypoint for the GenAI Agent service.
- Initializes the FastAPI app
- Registers routers: /diagnose (RCA pipeline) and /route (confidence routing, Week 4)
- Wires up the LangGraph StateGraph from app/graph/state_graph.py on startup
- Calls ml-engine's api/graph_traversal.py endpoint for dependency graph queries
  (see shared/api-contracts.md for the contract)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.schemas.incident import DiagnoseRequest, DiagnoseResponse
from app.graph.state_graph import pipeline


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

    return DiagnoseResponse(
        service_name=request.metrics.service_name,
        risk_score=result.get("risk_score", 0),
        risk_tier=result.get("risk_tier", "unknown"),
        prediction_confidence=result.get("prediction_confidence", 0),
        predicted_failure_type=result.get("predicted_failure_type", "none"),
        prediction_horizon_minutes=result.get("prediction_horizon_minutes", 0),
        root_cause_candidates_ranked=result.get("root_cause_candidates_ranked", []),
        guidance=result.get("guidance"),
        routing_decision=result.get("routing_decision", "escalate"),
    )


@app.get("/health", tags=["System"])
async def health():
    """Health check used by Docker and load balancers."""
    return {"status": "healthy", "service": "genai-agent", "version": "0.3.0"}


@app.get("/", tags=["System"])
async def root():
    return {
        "service": "Synapse RiskOps - GenAI Agent",
        "version": "0.3.0",
        "docs": "/docs",
        "endpoints": {
            "diagnose": "POST /diagnose",
            "health":   "GET /health",
        },
    }
