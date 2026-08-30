"""
genai-agent/app/schemas/incident.py
Owner: Person 1 | Week: 1-3

Pydantic models mirroring shared/schemas/incident_record.schema.json.
- Used for validating/serializing requests and responses in this service
  (diagnosis, guidance, routing blocks in particular)
- Keep in sync manually with the shared schema — do not let this drift
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class ServiceMetricsInput(BaseModel):
    """
    Metrics snapshot for a single service — mirrors ml-engine's
    ServiceMetricsInput so the genai-agent can forward it verbatim
    to POST /api/risk-score.
    """
    service_name: str
    cpu_usage: float
    memory_usage: float
    disk_io: float
    network_latency_ms: float
    request_count: int
    error_rate: float
    response_time_p99: float
    active_connections: int
    gc_pause_ms: float
    thread_count: int
    timestamp: Optional[str] = None


class DiagnoseRequest(BaseModel):
    """
    Request payload for POST /diagnose.
    - metrics: current service snapshot forwarded to ml-engine
    - logs: raw log entries for the LogAnalyzer agent
    """
    metrics: ServiceMetricsInput
    logs: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of log entries, each with at least 'service' and 'message' keys",
    )


class RootCauseCandidate(BaseModel):
    cause: str
    confidence: float
    affected_services: List[str] = Field(default_factory=list)
    reason: Optional[str] = None


class GuidanceBlock(BaseModel):
    summary: str = ""
    immediate_actions: List[str] = Field(default_factory=list)
    preventive_measures: List[str] = Field(default_factory=list)


class DiagnoseResponse(BaseModel):
    """
    Full pipeline output returned from POST /diagnose.
    Matches the diagnosis + guidance + routing blocks of
    shared/schemas/incident_record.schema.json.
    """
    service_name: str

    # ML Engine prediction
    risk_score: float
    risk_tier: str
    prediction_confidence: float
    predicted_failure_type: str
    prediction_horizon_minutes: int = 0

    # RCA agent output
    root_cause_candidates_ranked: List[RootCauseCandidate] = Field(default_factory=list)

    # Guidance agent output
    guidance: Optional[GuidanceBlock] = None

    # Routing decision
    routing_decision: str = "escalate"   # "auto_remediate" | "escalate"
