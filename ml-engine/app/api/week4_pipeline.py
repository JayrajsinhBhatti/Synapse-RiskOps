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

from typing import Optional, Dict, Any

class ServiceMetricsRequest(BaseModel):
    """
    Current metrics snapshot for one service.
    Supports both flat structure and nested {"service_name": ..., "metrics": {...}}.
    """
    service: Optional[str] = None
    service_name: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    disk_io: Optional[float] = None
    network_latency_ms: Optional[float] = None
    request_count: Optional[float] = None
    error_rate: Optional[float] = None
    response_time_p99: Optional[float] = None
    active_connections: Optional[float] = None
    gc_pause_ms: Optional[float] = None
    thread_count: Optional[float] = None

    class Config:
        extra = "allow"


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

    target_svc = request.service or request.service_name or "unknown-service"

    if request.metrics and isinstance(request.metrics, dict):
        m = request.metrics
        metrics = {
            "cpu_usage": float(m.get("cpu_usage", 0.0)),
            "memory_usage": float(m.get("memory_usage", 0.0)),
            "disk_io": float(m.get("disk_io", 0.0)),
            "network_latency_ms": float(m.get("network_latency_ms", 0.0)),
            "request_count": float(m.get("request_count", 0)),
            "error_rate": float(m.get("error_rate", 0.0)),
            "response_time_p99": float(m.get("response_time_p99", 0.0)),
            "active_connections": float(m.get("active_connections", 0)),
            "gc_pause_ms": float(m.get("gc_pause_ms", 0.0)),
            "thread_count": float(m.get("thread_count", 0)),
        }
    else:
        metrics = {
            "cpu_usage": float(request.cpu_usage or 0.0),
            "memory_usage": float(request.memory_usage or 0.0),
            "disk_io": float(request.disk_io or 0.0),
            "network_latency_ms": float(request.network_latency_ms or 0.0),
            "request_count": float(request.request_count or 0.0),
            "error_rate": float(request.error_rate or 0.0),
            "response_time_p99": float(request.response_time_p99 or 0.0),
            "active_connections": float(request.active_connections or 0.0),
            "gc_pause_ms": float(request.gc_pause_ms or 0.0),
            "thread_count": float(request.thread_count or 0.0),
        }

    # -------------------------------------------------
    # Execute ML + Graph analysis
    # -------------------------------------------------

    try:

        result = week4_pipeline.analyze_service(
            service=target_svc,
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