"""
Synapse RiskOps - Universal Metric Ingestion API
================================================
Provides a universal REST endpoint for services, scripts, and monitoring agents
to send real-time telemetry metrics directly to Synapse RiskOps without requiring
Prometheus or third-party infrastructure.

Endpoint: POST /api/v1/ingest/metrics (also aliased as /api/ingest/metrics)
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user_or_system
from app.core.database import get_db
from app.models.service import Service
from app.models.user import User
from app.schemas.ingest import MetricIngestPayload, MetricIngestResponse
from app.services.orchestrator import orchestrator
from app.services.sse_manager import sse_manager

logger = logging.getLogger("synapse.ingest")

router = APIRouter(
    tags=["Telemetry Ingestion"],
)


@router.post(
    "/api/v1/ingest/metrics",
    response_model=MetricIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Universal Telemetry Metric Ingestion (REST API / curl)",
)
@router.post(
    "/api/ingest/metrics",
    response_model=MetricIngestResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def ingest_metrics(
    payload: MetricIngestPayload,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_or_system),
):
    """
    Universal ingestion endpoint for incoming microservice metrics.
    Feeds telemetry directly into the Synapse ML Risk Engine and Orchestrator.
    """
    ts = payload.timestamp or datetime.now(timezone.utc).isoformat()
    service_name = payload.service_name.strip()

    # 1. Ensure service exists in Service Catalog
    svc_result = await db.execute(
        select(Service).where(Service.service_name == service_name)
    )
    service = svc_result.scalar_one_or_none()

    if service is None:
        service = Service(
            service_name=service_name,
            service_type="MICROSERVICE",
            criticality="HIGH" if any(k in service_name.lower() for k in ["pay", "order", "auth"]) else "MEDIUM",
            description=f"Auto-registered via universal REST metric ingestion ({payload.data_mode} mode)",
            is_active=True,
        )
        db.add(service)
        await db.commit()
        await db.refresh(service)
        logger.info(f"Auto-registered new service from metric ingest: '{service_name}'")

    # 2. Assemble standardized metrics dict
    metric_dict: Dict[str, float] = {}
    if payload.cpu_usage is not None:
        metric_dict["cpu_usage"] = float(payload.cpu_usage)
    if payload.memory_usage is not None:
        metric_dict["memory_usage"] = float(payload.memory_usage)
    if payload.error_rate is not None:
        metric_dict["error_rate"] = float(payload.error_rate)
    if payload.response_time_p99 is not None:
        metric_dict["response_time_p99"] = float(payload.response_time_p99)
    if payload.network_latency_ms is not None:
        metric_dict["network_latency_ms"] = float(payload.network_latency_ms)
    if payload.request_count is not None:
        metric_dict["request_count"] = float(payload.request_count)

    if payload.extra_metrics:
        for k, v in payload.extra_metrics.items():
            if isinstance(v, (int, float)):
                metric_dict[k] = float(v)

    # 3. Check for severe anomaly / threshold breach to route into ML pipeline
    err = metric_dict.get("error_rate", 0.0)
    cpu = metric_dict.get("cpu_usage", 0.0)
    p99 = metric_dict.get("response_time_p99", 0.0)

    is_anomaly = err >= 5.0 or cpu >= 75.0 or p99 >= 150.0
    incident_triggered = False
    anomaly_score = 0.85 if is_anomaly else 0.15

    if is_anomaly:
        try:
            await orchestrator.orchestrate_incident_lifecycle(
                service_name=service_name,
                metrics=metric_dict,
                environment="production",
                db=db,
                current_user=current_user,
                data_mode=payload.data_mode or "connected",
            )
            incident_triggered = True
        except Exception as e:
            logger.warning(f"Error executing orchestrator lifecycle for ingested metric: {e}")

    # 4. Broadcast real-time SSE telemetry event
    await sse_manager.broadcast(
        "telemetry_stream_update",
        {
            "service_name": service_name,
            "metrics": metric_dict,
            "timestamp": ts,
            "data_mode": payload.data_mode or "connected",
            "is_anomaly": is_anomaly,
        },
    )

    return MetricIngestResponse(
        status="ingested",
        service_name=service_name,
        timestamp=ts,
        metrics_received_count=len(metric_dict),
        data_mode=payload.data_mode or "connected",
        evaluated_anomaly=is_anomaly,
        anomaly_detected=is_anomaly,
        incident_triggered=incident_triggered,
        anomaly_score=anomaly_score,
        message=f"Ingested {len(metric_dict)} metrics for {service_name}. Pipeline evaluated.",
    )
