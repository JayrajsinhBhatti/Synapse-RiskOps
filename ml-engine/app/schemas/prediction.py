"""
Synapse RiskOps - Pydantic Schemas for ML Engine
==================================================
Owner: Person 2 | Week: 2

Request/response models for all ML Engine endpoints.
Response shapes align with shared/schemas/incident_record.schema.json
so that Person 1's GenAI agent can consume them directly.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# =====================================================
# Enums
# =====================================================

class RiskTier(str, Enum):
    """Risk classification tiers agreed in Week 2."""
    HEALTHY = "healthy"
    WATCH = "watch"
    CRITICAL = "critical"


class FailureType(str, Enum):
    """Predicted failure types the ML engine can identify."""
    CPU_SATURATION = "cpu_saturation"
    MEMORY_EXHAUSTION = "memory_exhaustion"
    DISK_IO_BOTTLENECK = "disk_io_bottleneck"
    LATENCY_DEGRADATION = "latency_degradation"
    ERROR_RATE_SPIKE = "error_rate_spike"
    CONNECTION_POOL_EXHAUSTION = "connection_pool_exhaustion"
    CASCADING_FAILURE = "cascading_failure"
    NONE = "none"


# =====================================================
# Request Schemas
# =====================================================

class ServiceMetricsInput(BaseModel):
    """
    Input payload for a single service's metrics snapshot.
    Matches the columns in sample_metrics.csv.
    """
    service_name: str = Field(..., description="Name of the microservice (e.g. 'api-gateway')")
    cpu_usage: float = Field(..., ge=0, le=100, description="CPU utilization percentage")
    memory_usage: float = Field(..., ge=0, le=100, description="Memory utilization percentage")
    disk_io: float = Field(..., ge=0, description="Disk I/O operations")
    network_latency_ms: float = Field(..., ge=0, description="Network latency in milliseconds")
    request_count: int = Field(..., ge=0, description="Number of requests in the current window")
    error_rate: float = Field(..., ge=0, description="Error rate percentage")
    response_time_p99: float = Field(..., ge=0, description="99th percentile response time (ms)")
    active_connections: int = Field(..., ge=0, description="Number of active connections")
    gc_pause_ms: float = Field(..., ge=0, description="Garbage collection pause time (ms)")
    thread_count: int = Field(..., ge=0, description="Number of active threads")
    timestamp: Optional[str] = Field(None, description="ISO8601 timestamp of the measurement")

    class Config:
        json_schema_extra = {
            "example": {
                "service_name": "order-service",
                "cpu_usage": 78.5,
                "memory_usage": 85.2,
                "disk_io": 32.1,
                "network_latency_ms": 45.3,
                "request_count": 5200,
                "error_rate": 8.5,
                "response_time_p99": 180.0,
                "active_connections": 120,
                "gc_pause_ms": 12.5,
                "thread_count": 48,
                "timestamp": "2026-07-04T14:30:00Z",
            }
        }


class RiskScoreRequest(BaseModel):
    """Request body for POST /api/risk-score."""
    metrics: ServiceMetricsInput


class BatchRiskScoreRequest(BaseModel):
    """Request body for batch risk scoring of multiple services."""
    services: List[ServiceMetricsInput]


# =====================================================
# Response Schemas
# =====================================================

class AnomalyDetail(BaseModel):
    """Details from the Isolation Forest anomaly detection model."""
    anomaly_score: float = Field(..., description="Raw anomaly score from Isolation Forest (0-1, higher = more anomalous)")
    is_anomaly: bool = Field(..., description="Whether the score exceeds the anomaly threshold")
    top_contributing_features: List[str] = Field(default_factory=list, description="Features most responsible for the anomaly")


class ForecastDetail(BaseModel):
    """Details from the Prophet/Statsmodels failure forecaster."""
    forecast_risk: float = Field(..., description="Forecasted risk level (0-1)")
    predicted_failure_type: str = Field(default="none", description="Type of predicted failure")
    prediction_horizon_minutes: int = Field(default=0, description="Minutes until predicted failure")
    trend_direction: str = Field(default="stable", description="Metric trend: rising, falling, stable")


class PredictionResponse(BaseModel):
    """
    Response from POST /api/risk-score.
    Aligns with shared/schemas/incident_record.schema.json -> prediction block.
    """
    predicted_at: str = Field(..., description="ISO8601 timestamp of when prediction was made")
    model_name: str = Field(default="synapse_riskops_v1", description="Model pipeline identifier")
    service_name: str = Field(..., description="Service that was scored")

    # Core risk output
    risk_score: float = Field(..., ge=0, le=100, description="Composite risk score (0-100)")
    risk_threshold: float = Field(default=75.0, description="Threshold for incident triggering")
    risk_tier: RiskTier = Field(..., description="Classified risk level: healthy / watch / critical")
    confidence: float = Field(..., ge=0, le=1, description="Model confidence (0-1)")

    # Failure prediction
    predicted_failure_type: str = Field(default="none", description="Type of predicted failure")
    prediction_horizon_minutes: int = Field(default=0, description="Minutes until predicted failure")

    # Sub-model details
    anomaly_detail: AnomalyDetail
    forecast_detail: ForecastDetail


class BatchPredictionResponse(BaseModel):
    """Response from batch risk scoring."""
    predictions: List[PredictionResponse]
    summary: dict = Field(default_factory=dict)


# =====================================================
# Ingest Schemas
# =====================================================

class IngestResponse(BaseModel):
    """Response from POST /api/ingest/metrics."""
    status: str = Field(default="success")
    rows_ingested: int = Field(..., description="Number of rows processed")
    services_found: List[str] = Field(default_factory=list)
    anomaly_count: int = Field(default=0, description="Number of anomaly-labeled rows (if ground truth present)")
    message: str = Field(default="")


class ModelStatusResponse(BaseModel):
    """Response for GET /api/model/status — reports training state."""
    anomaly_detector_trained: bool = False
    failure_forecaster_trained: bool = False
    training_samples: int = 0
    services_modeled: List[str] = Field(default_factory=list)
    last_trained_at: Optional[str] = None
