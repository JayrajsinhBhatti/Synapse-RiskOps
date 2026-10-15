"""
Synapse RiskOps - Dry-Run Twin Pydantic Schemas
===============================================
Defines contracts for counterfactual remediation simulations, side-by-side
candidate comparisons, uncertainty bounds, and separated execution authorization.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SecondaryFailureRisk(BaseModel):
    risk_type: str = Field(..., description="Type of potential secondary hazard (e.g. CACHE_STAMPEDE, CONNECTION_EXHAUSTION)")
    target_component: str = Field(..., description="Component or dependency vulnerable to secondary failure")
    probability: float = Field(..., ge=0.0, le=1.0, description="Estimated likelihood [0.0 - 1.0]")
    severity: str = Field(..., description="LOW, MEDIUM, HIGH, or CRITICAL")
    mitigation_hint: str = Field(..., description="Operational advice to prevent the secondary failure")


class CandidateActionSimulation(BaseModel):
    action: str = Field(..., description="Action identifier, e.g. RESTART_POD, SCALE_OUT_PODS, RATE_LIMIT_TRAFFIC")
    name: str = Field(..., description="Human-readable remediation name")
    description: str = Field(..., description="Operational mechanism")
    reversibility: str = Field(..., description="REVERSIBLE, PARTIALLY_REVERSIBLE, or IRREVERSIBLE")
    
    # Timing
    estimated_execution_seconds: float = Field(..., description="Predicted time to complete runbook execution")
    estimated_recovery_seconds: float = Field(..., description="Predicted time for metrics to stabilize post-execution")
    
    # Predicted Metrics
    predicted_health_score: float = Field(..., ge=0.0, le=100.0, description="Estimated post-remediation health score (0-100)")
    predicted_risk_score: float = Field(..., ge=0.0, le=100.0, description="Estimated post-remediation risk score (0-100)")
    health_delta: float = Field(..., description="Predicted health score improvement")
    risk_delta: float = Field(..., description="Predicted risk score reduction")
    predicted_error_rate: float = Field(..., ge=0.0, description="Estimated residual error rate percentage")
    predicted_p99_latency_ms: float = Field(..., ge=0.0, description="Estimated P99 response time in milliseconds")
    predicted_cpu_percent: float = Field(..., ge=0.0, description="Estimated CPU usage percentage")
    predicted_memory_percent: float = Field(..., ge=0.0, description="Estimated memory usage percentage")

    # Blast Radius & Cascade
    blast_radius_tier: str = Field(..., description="LOW, MODERATE, or HIGH")
    affected_downstream_services: List[str] = Field(default_factory=list, description="Downstream services with non-zero residual impact")
    protected_services_count: int = Field(default=0, description="Services insulated from cascading failure")

    # Secondary Failure Risks
    secondary_failure_risks: List[SecondaryFailureRisk] = Field(default_factory=list)
    secondary_failure_probability: float = Field(default=0.0, ge=0.0, le=1.0)

    # Uncertainty & Governance
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in simulation prediction")
    uncertainty_tier: str = Field(..., description="LOW, MEDIUM, or HIGH uncertainty")
    historical_sample_count: int = Field(default=0, description="Count of historical verified real-world runs used")
    can_auto_execute: bool = Field(..., description="Whether Autonomy Budget permits autonomous execution")
    approval_requirement: str = Field(..., description="AUTO_EXECUTABLE, REQUIRES_APPROVAL, or STRICT_HUMAN_APPROVAL")

    # Composite Ranking & Recommendation
    efficacy_score: float = Field(..., ge=0.0, le=100.0, description="Composite score factoring recovery, risk, and blast radius")
    is_recommended: bool = Field(default=False, description="Flag indicating if this is the top recommended action")
    recommendation_reason: str = Field(default="", description="Justification for recommendation or trade-off analysis")


class DryRunSimulateRequest(BaseModel):
    service_name: str = Field(..., description="Target service undergoing degradation or incident")
    incident_id: Optional[UUID] = Field(None, description="Associated incident ID if linked to an active incident")
    candidate_actions: Optional[List[str]] = Field(None, description="Optional subset of actions to simulate; if omitted, all standard candidates are evaluated")
    environment: str = Field(default="production", description="Environment context: production, staging, demo")
    current_metrics: Optional[Dict[str, float]] = Field(None, description="Telemetry snapshot: error_rate, response_time_p99, cpu_usage, memory_usage")


class DryRunSimulationResponse(BaseModel):
    simulation_id: UUID = Field(..., description="Unique simulation record identifier for auditing and replay")
    service_name: str = Field(..., description="Simulated target service")
    incident_id: Optional[UUID] = Field(None, description="Linked incident ID")
    timestamp: datetime = Field(..., description="Simulation timestamp (UTC)")
    
    baseline_telemetry: Dict[str, Any] = Field(..., description="Pre-simulation baseline telemetry metrics and health")
    candidate_simulations: List[CandidateActionSimulation] = Field(..., description="Side-by-side evaluated candidate actions")
    recommended_action: str = Field(..., description="Action ID of the top recommended remediation")
    
    model_version: str = Field(default="CounterfactualQueueingTwin-v1.2", description="Simulator model and ruleset version")
    assumptions: List[str] = Field(default_factory=list, description="Documented model assumptions and queuing parameters")
    limitations: List[str] = Field(default_factory=list, description="Explicit boundaries and missing data limitations")
    
    is_simulated: bool = Field(default=True, description="Strict safety flag: this payload represents simulated counterfactuals only")
    disclaimer: str = Field(
        default="This is a simplified counterfactual predictive simulator based on queueing models, dependency graph topology, and historical outcomes—not a full infrastructure digital twin. Never present simulated outcomes as guaranteed real-world results.",
        description="Mandatory disclaimer distinguishing predictive simulations from production state",
    )


class DryRunExecuteRequest(BaseModel):
    selected_action: Optional[str] = Field(None, description="Action to execute; defaults to the simulation's recommended action")
    approval_notes: Optional[str] = Field(None, description="Operator authorization notes or runbook justification")


class DryRunExecuteResponse(BaseModel):
    simulation_id: UUID
    executed_action: str
    target_service: str
    execution_status: str
    ansible_task_id: Optional[str] = None
    semaphore_url: Optional[str] = None
    remediation_record_id: Optional[str] = None
    message: str
