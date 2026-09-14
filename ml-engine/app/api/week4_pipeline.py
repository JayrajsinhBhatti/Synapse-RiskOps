"""
Synapse RiskOps - Week 4 Pipeline API
=====================================

Owner: Person 2 | Week: 4

Real ML → Graph integration endpoint.

Flow:

    Metrics
        ↓
    RiskEngine
        ↓
    Prediction
        ↓
    Dependency Graph
        ↓
    RCA Context
        ↓
    Person 1 Confidence Router
        ↓
    Routing Decision
        ↓
    Runbook
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.schemas.prediction import FailureType
from app.services.week4_pipeline import week4_pipeline


router = APIRouter(
    prefix="/api/week4",
    tags=["Week 4 Pipeline"],
)


# =====================================================
# REQUEST MODELS
# =====================================================

class ServiceMetricsRequest(BaseModel):
    """
    Current metrics snapshot for one service.
    """

    service: str = Field(
        ...,
        min_length=1,
        description="Service name",
    )

    cpu_usage: float

    memory_usage: float

    disk_io: float

    network_latency_ms: float

    request_count: float

    error_rate: float

    response_time_p99: float

    active_connections: float

    gc_pause_ms: float

    thread_count: float


class RoutingExecutionRequest(BaseModel):
    """
    Routing decision returned by Person 1's confidence router.
    """

    service: str = Field(
        ...,
        min_length=1,
    )

    failure_type: FailureType

    routing_decision: str = Field(
        ...,
        pattern="^(auto_remediate|escalate)$",
    )

    routing_confidence: float = Field(
        ...,
        ge=0,
        le=1,
    )


# =====================================================
# REAL ML → GRAPH PIPELINE
# =====================================================

@router.post("/analyze")
async def analyze_service(
    request: ServiceMetricsRequest,
):
    """
    Run the real ML + dependency graph analysis.

    Flow:

        Metrics
            ↓
        RiskEngine.score()
            ↓
        PredictionResponse
            ↓
        GraphBuilder.rank_root_cause_candidates()
            ↓
        Diagnosis Context
    """

    # -------------------------------------------------
    # IMPORTANT:
    # Import inside the function to avoid circular import.
    #
    # main.py imports this router.
    # Therefore this import must NOT be at module level.
    # -------------------------------------------------

    from app.main import get_risk_engine

    engine = get_risk_engine()

    if engine is None or not engine.is_trained:
        raise HTTPException(
            status_code=503,
            detail=(
                "Risk Engine not ready. "
                "Models have not been trained yet."
            ),
        )

    # -------------------------------------------------
    # Convert request into the dictionary expected
    # by RiskEngine.score()
    # -------------------------------------------------

    metrics = {
        "cpu_usage": request.cpu_usage,
        "memory_usage": request.memory_usage,
        "disk_io": request.disk_io,
        "network_latency_ms": request.network_latency_ms,
        "request_count": request.request_count,
        "error_rate": request.error_rate,
        "response_time_p99": request.response_time_p99,
        "active_connections": request.active_connections,
        "gc_pause_ms": request.gc_pause_ms,
        "thread_count": request.thread_count,
    }

    # -------------------------------------------------
    # Execute ML + Graph analysis
    # -------------------------------------------------

    try:

        result = week4_pipeline.analyze_service(
            service=request.service,
            metrics=metrics,
            risk_engine=engine,
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Week 4 analysis failed: {str(e)}",
        )

    # -------------------------------------------------
    # Return prediction + diagnosis context
    # -------------------------------------------------

    return {
        "prediction": result["prediction"],
        "diagnosis_context": result["diagnosis_context"],
    }


# =====================================================
# ROUTING → RUNBOOK EXECUTION
# =====================================================

@router.post("/execute")
async def execute_decision(
    request: RoutingExecutionRequest,
):
    """
    Execute the routing decision.

    auto_remediate
        ↓
    Runbook Engine
        ↓
    Simulated remediation

    escalate
        ↓
    Human review
        ↓
    No remediation
    """

    try:

        result = week4_pipeline.execute_decision(
            service=request.service,
            failure_type=request.failure_type,
            routing_decision=request.routing_decision,
            routing_confidence=request.routing_confidence,
        )

        return result

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Runbook execution failed: {str(e)}",
        )