"""
Synapse RiskOps - Reliability Analytics & Telemetry Schemas
===========================================================
Schemas for computed reliability metrics, time-series telemetry,
and change event correlation.
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ServiceReliabilityScore(BaseModel):
    service_id: Optional[UUID] = None
    service_name: str
    criticality: str
    reliability_score: float = Field(..., description="Percentage uptime/reliability 0-100")
    incident_count_7d: int
    avg_mttr_minutes: float
    health_status: str = Field(..., description="HEALTHY, WATCH, CRITICAL")


class DailyIncidentFrequency(BaseModel):
    date: str
    total: int
    critical: int
    high: int
    medium: int
    low: int


class ReliabilityAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # Core Computed Reliability KPIs
    mttr_minutes: float = Field(..., description="Average Mean Time to Resolution in minutes")
    mttr_formatted: str = Field(..., description="Human readable MTTR, e.g. '2m 45s'")
    mttr_trend_pct: float = Field(..., description="Trend percentage change vs 30d baseline")
    mttd_minutes: float = Field(..., description="Average Mean Time to Detection in minutes")
    mttd_formatted: str = Field(..., description="Human readable MTTD")
    
    # System Health & Incident Counts
    system_health_pct: float = Field(..., description="Computed platform health percentage")
    active_incidents_count: int
    critical_incidents_count: int
    resolved_incidents_count: int
    total_incidents_count: int
    services_monitored_count: int

    # Breakdown by severity & daily history
    severity_distribution: Dict[str, int]
    daily_frequency_7d: List[DailyIncidentFrequency]
    service_scores: List[ServiceReliabilityScore]


class MetricDataPoint(BaseModel):
    timestamp: str
    cpu_usage: float
    memory_usage: float
    latency_p99: float
    latency_p95: float
    error_rate: float
    requests_per_sec: float
    connection_pool: float


class ServiceMetricsResponse(BaseModel):
    service_id: Optional[str] = None
    service_name: str
    timeframe: str
    sample_interval: str
    thresholds: Dict[str, float]
    points: List[MetricDataPoint]


class ChangeEventResponse(BaseModel):
    id: str
    timestamp: datetime
    service_name: str
    change_type: str = Field(..., description="DEPLOYMENT, CONFIG_PUSH, CANARY_PROMOTION, SCALE_EVENT")
    title: str
    description: str
    author: str
    commit_sha: Optional[str] = None
    rollback_supported: bool = True
    correlated_with_incident: bool = False


class SimilarIncidentItem(BaseModel):
    id: UUID
    title: str
    severity: str
    status: str
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    duration_formatted: str
    predicted_failure_type: Optional[str] = None
    root_cause: Optional[str] = None
    guidance: Optional[str] = None
    resolution_action: Optional[str] = None
    similarity_score: float
