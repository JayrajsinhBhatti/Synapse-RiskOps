"""
Synapse RiskOps - System Mode, Connection Verification, and Retention Schemas
=============================================================================
Defines Pydantic schemas for runtime mode switching, connection verification probes,
and time-based log retention configuration.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SystemModeResponse(BaseModel):
    """Current operational mode and connectivity metadata."""
    mode: str = Field(..., description="'demo' or 'connected'")
    is_live_telemetry_active: bool = False
    external_app_connected: bool = False
    external_app_info: Optional[Dict[str, Any]] = None
    prometheus_url: Optional[str] = None
    telemetry_bridge_url: Optional[str] = None
    connected_services: List[str] = []
    updated_at: Optional[datetime] = None


class ConnectDemoAppRequest(BaseModel):
    """Admin request to connect or disconnect the external 10-microservice demo application."""
    action: str = Field("connect", description="'connect' or 'disconnect'")
    gateway_url: Optional[str] = Field("http://localhost:9101", description="Demo API Gateway base URL")


class ConnectDemoAppResponse(BaseModel):
    """Response returned upon connecting or disconnecting the demo application."""
    success: bool
    mode: str
    external_app_connected: bool
    services: List[str] = []
    message: str
    timestamp: str



class SystemModeUpdateRequest(BaseModel):
    """Update runtime operational mode."""
    mode: str = Field(..., pattern="^(demo|connected)$", description="'demo' or 'connected'")
    connection_config: Optional[Dict[str, Any]] = None


class ConnectionVerificationRequest(BaseModel):
    """Payload to test and verify live telemetry connection."""
    connection_method: str = Field("prometheus", description="'prometheus', 'opentelemetry', 'rest_api', 'csv_upload', or 'synapse-cluster'")
    prometheus_url: Optional[str] = Field("http://localhost:9090", description="Prometheus base URL")
    telemetry_bridge_url: Optional[str] = Field("http://localhost:9010", description="Telemetry Bridge URL")
    auth_type: Optional[str] = Field("none", description="'none', 'bearer', or 'basic'")
    auth_token: Optional[str] = None
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None
    target_services: Optional[List[str]] = None
    backfill_hours: Optional[int] = Field(0, description="Hours of historical metrics to backfill (0, 24, 48)")


class ServiceMetricStatus(BaseModel):
    """Status of telemetry stream for an individual microservice."""
    service_name: str
    status: str = "active" # active, waiting, degraded
    metrics_received: int = 8
    total_expected_metrics: int = 8
    metrics_sample: Dict[str, Any] = {}


class VerificationCheckItem(BaseModel):
    """Single verification check status."""
    name: str
    passed: bool
    message: str


class ConnectionVerificationResponse(BaseModel):
    """Comprehensive report returned by live connectivity probe."""
    verified: bool
    prometheus_reachable: bool
    services_discovered: List[str] = []
    service_metric_statuses: List[ServiceMetricStatus] = []
    telemetry_stream_active: bool = False
    ml_readiness_pct: int = 80 # Dynamic ML warmup/readiness percentage
    backfill_completed: bool = False
    backfill_points_loaded: int = 0
    active_metric_sample: Optional[Dict[str, Any]] = None
    topology_node_count: int = 0
    checks: List[VerificationCheckItem] = []
    timestamp: str


class BackfillRequest(BaseModel):
    """Request to backfill historical metrics from Prometheus to solve cold-start."""
    hours: int = Field(24, ge=1, le=72, description="Number of hours to backfill (e.g. 24 or 48)")
    prometheus_url: Optional[str] = Field("http://localhost:9090", description="Prometheus base URL")
    auth_type: Optional[str] = "none"
    auth_token: Optional[str] = None
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None
    services: Optional[List[str]] = None


class BackfillResponse(BaseModel):
    """Response returned upon completing Prometheus historical backfill."""
    status: str = "backfill_completed"
    hours_backfilled: int
    services_backfilled: int
    data_points_loaded: int
    ml_baseline_calibrated: bool = True
    message: str


class RetentionSettingItem(BaseModel):
    """Single module retention policy."""
    module: str = Field(..., description="'incidents' or 'risk_assessments'")
    retention_period: str = Field("all", pattern="^(1d|7d|30d|90d|all)$")
    auto_purge_enabled: bool = True
    last_purged_at: Optional[datetime] = None
    records_purged_last: int = 0


class RetentionSettingsResponse(BaseModel):
    """All configured module retention policies."""
    policies: List[RetentionSettingItem]
    supported_periods: List[str] = ["1d", "7d", "30d", "90d", "all"]


class RetentionUpdateRequest(BaseModel):
    """Request to update retention period for a module."""
    module: str = Field(..., pattern="^(incidents|risk_assessments)$")
    retention_period: str = Field(..., pattern="^(1d|7d|30d|90d|all)$")
    auto_purge_enabled: Optional[bool] = True


class RetentionPurgeResponse(BaseModel):
    """Results of executing timestamp-based retention purge."""
    module: str
    retention_period: str
    cutoff_timestamp: Optional[str] = None
    records_deleted: int
    purged_at: str
    message: str
