"""
Synapse RiskOps - Cascade Interception Planner Pydantic Schemas
==============================================================
Data contracts for simulating failure propagation, generating and ranking
protective interception plans, and executing safe interventions.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class PropagationHop(BaseModel):
    """Represents a single step in the cascading failure propagation wave."""

    service_name: str
    depth: int = Field(..., description="Hop distance from failing seed service")
    propagation_probability: float = Field(..., description="Estimated probability of failure transmission (0.0 - 1.0)")
    estimated_time_to_impact_seconds: float = Field(..., description="Seconds until caller is impacted")
    criticality: str = Field(..., description="'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'")
    service_type: str = Field(..., description="'GATEWAY', 'MICROSERVICE', 'DATABASE', etc.")
    impact_mechanism: str = Field(..., description="e.g. 'Thread pool timeout', 'Retry storm amplification'")
    is_seed: bool = False


class CascadePath(BaseModel):
    """A sequence of service names representing a propagation path."""

    path: List[str]
    depth: int
    vulnerability_score: float


class CascadeSimulationResult(BaseModel):
    """Output of failure propagation simulation before any intervention."""

    seed_service: str
    failure_type: str
    total_services: int
    at_risk_count: int
    blast_radius_percent: float
    criticality_weighted_impact: float
    propagation_timeline: List[PropagationHop]
    propagation_paths: List[CascadePath]
    at_risk_services: List[str]
    critical_services_threatened: List[str]
    unaffected_services: List[str]
    assumptions_and_evidence: List[str]
    simulation_label: str = "SIMULATED_ESTIMATE"


class InterceptionAction(BaseModel):
    """Individual protective intervention action within an interception plan."""

    action_type: str = Field(..., description="e.g. 'CIRCUIT_BREAKER_TRIP', 'RATE_LIMIT_GATEWAY', 'SCALE_OUT_PODS', 'REDUCE_RETRIES', 'ISOLATE_DEPENDENCY'")
    target_service: str
    parameter: Optional[str] = None
    description: str
    reversibility: str = Field(..., description="'REVERSIBLE', 'PARTIALLY_REVERSIBLE', 'IRREVERSIBLE'")
    estimated_execution_seconds: float
    estimated_recovery_seconds: float
    disruption_score: float = Field(..., description="Impact on benign traffic (0 to 100)")
    autonomy_risk_level: str = Field(..., description="'LOW', 'MEDIUM', 'HIGH'")
    autonomy_decision: str = Field(..., description="'AUTO_EXECUTE' or 'REQUIRE_APPROVAL'")


class InterceptionPlan(BaseModel):
    """A prioritized, coherent bundle of actions to intercept failure propagation."""

    plan_id: str
    name: str
    strategy: str = Field(..., description="'SURGICAL_CIRCUIT_BREAKER', 'EDGE_TRAFFIC_SHEDDING', 'ELASTIC_SCALE_OUT', 'MULTI_LAYER_CONTAINMENT'")
    rank: int = Field(..., description="1 = Recommended Best Plan")
    is_recommended: bool = False
    actions: List[InterceptionAction]

    # Before vs After Impact Comparison
    blast_radius_before_percent: float
    blast_radius_after_percent: float
    blast_radius_reduction_percent: float
    services_at_risk_before: int
    services_at_risk_after: int
    services_protected_count: int
    protected_services_list: List[str]
    residual_at_risk_services: List[str]

    # Evaluation Scores
    overall_efficacy_score: float = Field(..., description="0 to 100")
    composite_utility_score: float = Field(..., description="Efficacy weighted against disruption and risk")
    disruption_level: str = Field(..., description="'MINIMAL', 'LOW', 'MODERATE', 'HIGH'")
    estimated_total_recovery_seconds: float

    # Autonomy & Governance
    autonomy_tier: str = Field(..., description="'AUTO_EXECUTE' or 'REQUIRE_APPROVAL'")
    requires_human_approval: bool
    governance_reasoning: str
    architectural_rationale: str


class CascadeSimulateRequest(BaseModel):
    """Input payload to simulate cascading failure and generate interception plans."""

    seed_service: str = Field(..., description="Initially degraded or failing service")
    failure_type: str = Field(default="latency_spike", description="'latency_spike', 'error_storm', 'memory_exhaustion', 'connection_pool_saturation', 'service_crash'")
    severity: float = Field(default=0.85, ge=0.1, le=1.0, description="Severity factor of initial seed failure")
    active_incident_id: Optional[UUID] = None


class CascadeSimulationResponse(BaseModel):
    """Full analysis with baseline cascade simulation and ranked interception plans."""

    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    seed_service: str
    failure_type: str
    simulation: CascadeSimulationResult
    candidate_plans: List[InterceptionPlan]
    recommended_plan: Optional[InterceptionPlan] = None
    graph_topology_summary: Dict[str, Any]


class CascadeExecutePlanRequest(BaseModel):
    """Request to safely execute an interception plan under Autonomy Budget governance."""

    plan_id: str
    seed_service: str
    strategy: str
    incident_id: Optional[UUID] = None
    approval_notes: Optional[str] = None


class CascadeExecutePlanResponse(BaseModel):
    """Execution status and audit record for dispatched interception plan."""

    plan_id: str
    status: str = Field(..., description="'DISPATCHED', 'BLOCKED_APPROVAL_REQUIRED', 'REJECTED'")
    remediation_record_ids: List[UUID]
    ansible_task_ids: List[str]
    dispatched_actions: List[str]
    execution_duration_seconds: float
    audit_log_ids: List[UUID]
    message: str
