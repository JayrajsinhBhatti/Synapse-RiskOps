"""
Synapse RiskOps - Risk Score API
=================================
Owner: Person 2 | Week: 2

POST /api/risk-score — the primary endpoint consumed by Person 1's GenAI agent.
Accepts a service's metrics snapshot, runs it through the RiskEngine
(Isolation Forest + Statsmodels), and returns a composite risk assessment.

Response shape aligns with shared/schemas/incident_record.schema.json -> prediction.
"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.schemas.prediction import (
    RiskScoreRequest,
    BatchRiskScoreRequest,
    PredictionResponse,
    BatchPredictionResponse,
    ModelStatusResponse,
)

router = APIRouter(prefix="/api", tags=["Risk Scoring"])


@router.post("/risk-score", response_model=PredictionResponse)
async def compute_risk_score(request: RiskScoreRequest):
    """
    Compute the composite risk score for a single service.

    This is the primary endpoint for Person 1's GenAI agent:
    - Accepts a service's current metrics snapshot
    - Runs Isolation Forest anomaly detection
    - Runs Statsmodels failure forecasting
    - Returns a weighted composite risk score (0-100) with tier classification

    Risk Tiers:
    - HEALTHY (< 40): Normal operation
    - WATCH (40-75): Elevated risk, monitoring recommended
    - CRITICAL (>= 75): Incident-triggering, triggers Person 1's RCA pipeline
    """
    from app.main import get_risk_engine

    engine = get_risk_engine()
    if engine is None or not engine.is_trained:
        raise HTTPException(
            status_code=503,
            detail="Risk engine not ready. Models have not been trained yet. "
                   "POST /api/ingest/metrics with training data first.",
        )

    metrics_dict = request.metrics.model_dump(exclude={"service_name", "timestamp"})

    try:
        result = engine.score(
            service_name=request.metrics.service_name,
            metrics=metrics_dict,
        )
        logger.info(
            f"Risk score for {request.metrics.service_name}: "
            f"{result.risk_score} ({result.risk_tier.value})"
        )
        return result

    except Exception as e:
        logger.error(f"Risk scoring failed: {e}")
        raise HTTPException(status_code=500, detail=f"Risk scoring error: {str(e)}")


@router.post("/risk-score/batch", response_model=BatchPredictionResponse)
async def compute_batch_risk_scores(request: BatchRiskScoreRequest):
    """
    Compute risk scores for multiple services in a single request.
    Useful for dashboard polling and bulk assessment.
    """
    from app.main import get_risk_engine

    engine = get_risk_engine()
    if engine is None or not engine.is_trained:
        raise HTTPException(
            status_code=503,
            detail="Risk engine not ready. Models have not been trained yet.",
        )

    predictions = []
    critical_count = 0
    watch_count = 0

    for svc_metrics in request.services:
        metrics_dict = svc_metrics.model_dump(exclude={"service_name", "timestamp"})

        try:
            result = engine.score(
                service_name=svc_metrics.service_name,
                metrics=metrics_dict,
            )
            predictions.append(result)

            if result.risk_tier.value == "critical":
                critical_count += 1
            elif result.risk_tier.value == "watch":
                watch_count += 1

        except Exception as e:
            logger.error(f"Batch scoring failed for {svc_metrics.service_name}: {e}")

    summary = {
        "total_services": len(request.services),
        "scored": len(predictions),
        "critical": critical_count,
        "watch": watch_count,
        "healthy": len(predictions) - critical_count - watch_count,
    }

    return BatchPredictionResponse(predictions=predictions, summary=summary)


@router.get("/model/status", response_model=ModelStatusResponse)
async def get_model_status():
    """
    Check the current training status of the ML models.
    Useful for frontend health indicators and debugging.
    """
    from app.main import get_risk_engine

    engine = get_risk_engine()
    if engine is None:
        return ModelStatusResponse()

    status = engine.get_status()
    return ModelStatusResponse(**status)
