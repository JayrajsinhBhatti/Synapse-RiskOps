"""
Synapse RiskOps - Autonomy Budget ORM Models
============================================
Defines database persistence for:
1. RemediationRecord: Tracks every proposed, evaluated, approved, and executed remediation.
2. AutonomyAuditLog: Tamper-evident audit trail of all autonomy decisions and approvals.
3. AutonomyPolicyModel: Configurable organization-wide autonomy and error budget policies.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class RemediationRecord(Base):
    """
    Tracks every remediation request evaluated by the Autonomy Budget Engine,
    recording pre-execution estimates, approval workflow, and actual post-execution recovery.
    """

    __tablename__ = "remediation_records"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    incident_id = Column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    service_name = Column(String(100), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    runbook_id = Column(String(100), nullable=True)

    # Risk & Policy Evaluation
    risk_level = Column(String(20), nullable=False, default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    autonomy_decision = Column(String(30), nullable=False)  # AUTO_EXECUTE, REQUIRE_APPROVAL, REJECTED
    approval_status = Column(String(30), nullable=False, default="PENDING")  # AUTO_APPROVED, PENDING, APPROVED, REJECTED
    status = Column(String(30), nullable=False, default="PROPOSED")  # PROPOSED, PENDING_APPROVAL, EXECUTING, COMPLETED, FAILED, REJECTED, TIMEOUT

    # Human Approval
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_username = Column(String(100), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Timing Estimates
    estimated_execution_seconds = Column(Float, nullable=True)
    estimated_recovery_seconds = Column(Float, nullable=True)
    estimate_source = Column(String(30), nullable=False, default="calculated")  # historical, calculated, predicted, insufficient_data
    estimate_uncertainty = Column(String(50), nullable=True)
    estimate_display = Column(Text, nullable=True)

    # Actual Measured Results
    actual_execution_seconds = Column(Float, nullable=True)
    actual_recovery_seconds = Column(Float, nullable=True)
    success = Column(Boolean, nullable=True)
    post_remediation_health = Column(String(50), nullable=True)  # HEALTHY, DEGRADED, UNSTABLE, FAILED

    # Execution Details
    ansible_task_id = Column(String(100), nullable=True)
    semaphore_url = Column(Text, nullable=True)
    execution_logs = Column(JSONB, nullable=True)
    pre_metrics = Column(JSONB, nullable=True)
    post_metrics = Column(JSONB, nullable=True)

    # Reasoning and Auditing
    reasoning = Column(Text, nullable=True)
    evaluation_factors = Column(JSONB, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    executed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class AutonomyAuditLog(Base):
    """
    Immutable audit trail for all autonomy decisions, approval overrides, and dispatches.
    """

    __tablename__ = "autonomy_audit_logs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    remediation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("remediation_records.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    event_type = Column(String(50), nullable=False, index=True)  # EVALUATED, AUTO_EXECUTED, APPROVAL_REQUESTED, APPROVED, REJECTED, EXECUTED, FAILED, RECOVERY_VERIFIED
    service_name = Column(String(100), nullable=False)
    action = Column(String(100), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_role = Column(String(50), nullable=True)
    user_username = Column(String(100), nullable=True)
    decision = Column(String(30), nullable=True)
    details = Column(JSONB, nullable=True)

    timestamp = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )


class AutonomyPolicyModel(Base):
    """
    Configurable organizational policies for Autonomy Budget.
    """

    __tablename__ = "autonomy_policies"

    id = Column(String(50), primary_key=True, default="default")
    low_risk_auto_execute = Column(Boolean, nullable=False, default=True)
    medium_risk_requires_approval = Column(Boolean, nullable=False, default=True)
    critical_services_always_require_approval = Column(Boolean, nullable=False, default=True)
    min_historical_samples = Column(Float, nullable=False, default=3.0)
    error_budget_threshold_percent = Column(Float, nullable=False, default=20.0)
    max_auto_recovery_time_seconds = Column(Float, nullable=False, default=60.0)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
