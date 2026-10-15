"""
Synapse RiskOps - Dry-Run Twin ORM Models
=========================================
Stores counterfactual simulation runs for predictive remediation:
1. DryRunSimulationRecord: Records simulation inputs, baseline metrics, candidate
   remediations evaluated, predicted telemetry, blast radius, secondary risks,
   assumptions, and recommendation.
2. Tracks separated authorized execution if an operator subsequently dispatches
   a validated action.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.core.database import Base


class DryRunSimulationRecord(Base):
    """
    Immutable audit record of a counterfactual remediation simulation.
    Preserves exact inputs, model/rule assumptions, timestamp, and predicted outcomes
    to ensure reproducibility and transparent auditability without mutating live systems.
    """

    __tablename__ = "dry_run_simulations"

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
    environment = Column(String(50), nullable=False, default="production")

    # Baseline & Counterfactual Candidates (stored as JSON)
    baseline_metrics = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict)
    candidate_actions = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list)

    # Recommendation
    recommended_action = Column(String(100), nullable=False)
    recommendation_reason = Column(Text, nullable=True)

    # Assumptions, limitations, evidence
    assumptions = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list)
    limitations = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list)
    model_version = Column(String(50), nullable=False, default="CounterfactualQueueingTwin-v1.2")

    # Safe separation flag
    is_simulated = Column(Boolean, nullable=False, default=True)

    # Authorized Execution link (only populated when user explicitly executes approved plan)
    executed_action = Column(String(100), nullable=True)
    executed_at = Column(DateTime(timezone=True), nullable=True)
    executed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    executed_by_username = Column(String(100), nullable=True)
    remediation_record_id = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
