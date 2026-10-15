"""
Synapse RiskOps - Autonomy Budget Pydantic Schemas
==================================================
Request and response models for evaluating, executing, approving,
and auditing remediation actions through the Autonomy Budget Engine.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class TimingEstimate(BaseModel):
    """Execution and recovery timing estimates."""

    estimated_execution_seconds: Optional[float] = None
    estimated_recovery_seconds: Optional[float] = None
    source: str = Field(..., description="'historical', 'calculated', 'predicted', or 'insufficient_data'")
    uncertainty: Optional[str] = None
    display_text: str
    historical_sample_count: int = 0


class AutonomyEvaluationRequest(BaseModel):
    """Request to evaluate a proposed remediation action against autonomy budget."""

    service_name: str = Field(..., description="Target service to remediate")
    action: str = Field(..., description="Action name (e.g. SCALE_OUT_PODS, RESTART_CONNECTION_POOL)")
    runbook_id: Optional[str] = None
    incident_id: Optional[UUID] = None
    current_metrics: Optional[Dict[str, float]] = None
    parameters: Optional[Dict[str, Any]] = None
    risk_tier: Optional[str] = Field(default=None, description="Risk tier e.g. 'HEALTHY', 'WATCH', 'CRITICAL'")
    risk_score: Optional[float] = Field(default=None, description="Current composite risk score (0-100)")
    incident_criticality: Optional[str] = Field(default=None, description="Criticality level ('LOW', 'MEDIUM', 'MID', 'HIGH', 'CRITICAL')")
    auto_execute_if_cleared: Optional[bool] = Field(default=False, description="Automatically execute if policy evaluates to AUTO_EXECUTE")


class AutonomyEvaluationResponse(BaseModel):
    """Evaluation result determining if action can auto-execute or requires approval."""

    decision: str = Field(..., description="'AUTO_EXECUTE', 'REQUIRE_APPROVAL', or 'REJECTED'")
    risk_level: str = Field(..., description="'LOW', 'MEDIUM', or 'HIGH'")
    service_name: str
    service_criticality: str = Field(..., description="'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'")
    incident_criticality: Optional[str] = None
    human_in_the_loop_required: bool = False
    action: str
    reversibility: str = Field(..., description="'REVERSIBLE', 'PARTIALLY_REVERSIBLE', 'IRREVERSIBLE'")
    blast_radius: str = Field(..., description="'LOW', 'MODERATE', 'HIGH'")
    action_reliability: float = Field(..., description="Historical success rate (0.0 to 1.0)")
    error_budget_remaining_percent: float = Field(..., description="Remaining service reliability/error budget (0-100)")
    timing_estimate: TimingEstimate
    approval_required: bool
    approval_status: Optional[str] = "PENDING"
    approved_by_username: Optional[str] = None
    rejection_reason: Optional[str] = None
    allowed_roles: List[str] = Field(default_factory=lambda: ["ADMIN", "OPERATOR"])
    reasoning: str
    factors: List[str] = Field(default_factory=list)
    remediation_record_id: Optional[UUID] = None
    executed: bool = False
    execution_result: Optional[Dict[str, Any]] = None


class AutonomyExecuteRequest(BaseModel):
    """Request to execute a remediation action with autonomy enforcement."""

    service_name: str
    action: str
    incident_id: Optional[UUID] = None
    remediation_record_id: Optional[UUID] = None
    approval_notes: Optional[str] = None


class AutonomyApprovalRequest(BaseModel):
    """Human approval or rejection for a pending remediation."""

    remediation_record_id: UUID
    approved: bool = True
    reason: Optional[str] = None


class AutonomyVerifyRecoveryRequest(BaseModel):
    """Request to poll and record post-remediation recovery metrics."""

    remediation_record_id: UUID
    current_metrics: Optional[Dict[str, float]] = None


class RemediationRecordResponse(BaseModel):
    """Historical remediation record with timing estimates vs actual outcomes."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    incident_id: Optional[UUID] = None
    service_name: str
    action: str
    runbook_id: Optional[str] = None
    risk_level: str
    autonomy_decision: str
    approval_status: str
    status: str
    approved_by_username: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    estimated_execution_seconds: Optional[float] = None
    estimated_recovery_seconds: Optional[float] = None
    estimate_source: str
    estimate_uncertainty: Optional[str] = None
    estimate_display: Optional[str] = None
    actual_execution_seconds: Optional[float] = None
    actual_recovery_seconds: Optional[float] = None
    success: Optional[bool] = None
    post_remediation_health: Optional[str] = None
    ansible_task_id: Optional[str] = None
    semaphore_url: Optional[str] = None
    reasoning: Optional[str] = None
    evaluation_factors: Optional[List[str]] = None
    created_at: datetime
    executed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class AutonomyAuditLogResponse(BaseModel):
    """Audit log entry for an autonomy decision or approval."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    remediation_id: Optional[UUID] = None
    event_type: str
    service_name: str
    action: str
    user_username: Optional[str] = None
    user_role: Optional[str] = None
    decision: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime


class AutonomyPolicyUpdate(BaseModel):
    """Policy update payload."""

    low_risk_auto_execute: Optional[bool] = None
    medium_risk_requires_approval: Optional[bool] = None
    critical_services_always_require_approval: Optional[bool] = None
    min_historical_samples: Optional[float] = None
    error_budget_threshold_percent: Optional[float] = None
    max_auto_recovery_time_seconds: Optional[float] = None


class AutonomyBudgetStatusResponse(BaseModel):
    """Overview of organization autonomy budget, policies, and active operations."""

    policy: Dict[str, Any]
    active_remediations_count: int
    pending_approvals_count: int
    executed_24h_count: int
    auto_executed_24h_count: int
    services_criticality: Dict[str, str]
    services_error_budget: Dict[str, float]
