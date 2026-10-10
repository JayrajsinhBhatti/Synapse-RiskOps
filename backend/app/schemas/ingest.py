"""
Synapse RiskOps - REST API Metric Ingestion Schemas
===================================================
Defines schemas for universal HTTP metric ingestion from microservices,
custom scripts (curl, python, node.js, java), and monitoring agents.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class MetricIngestPayload(BaseModel):
    """
    Universal metric payload:
    POST /api/v1/ingest/metrics
    """
    service_name: str = Field(..., description="Target service reporting telemetry, e.g. 'payment-service'")
    cpu_usage: Optional[float] = Field(None, description="CPU usage % (0-100)")
    memory_usage: Optional[float] = Field(None, description="Memory usage % (0-100)")
    error_rate: Optional[float] = Field(None, description="Error rate % (0-100)")
    response_time_p99: Optional[float] = Field(None, description="P99 response time / latency in ms")
    network_latency_ms: Optional[float] = Field(None, description="Network round-trip latency in ms")
    request_count: Optional[float] = Field(None, description="Requests per second or count")
    timestamp: Optional[str] = Field(None, description="ISO timestamp of metric event")
    data_mode: Optional[str] = Field("connected", description="'demo' or 'connected'")
    extra_metrics: Optional[Dict[str, float]] = Field(default_factory=dict, description="Additional custom telemetry attributes")


class MetricIngestResponse(BaseModel):
    """Response returned upon successful telemetry metric ingestion."""
    status: str = "ingested"
    service_name: str
    timestamp: str
    metrics_received_count: int
    data_mode: str
    evaluated_anomaly: bool = False
    anomaly_detected: bool = False
    incident_triggered: bool = False
    anomaly_score: Optional[float] = None
    message: str = "Telemetry metrics successfully ingested into Synapse RiskOps pipeline."
