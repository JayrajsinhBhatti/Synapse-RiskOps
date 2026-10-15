"""
Synapse RiskOps - Chaos-Calibrated Causal Graph ORM Models
=========================================================
Stores:
1. CausalEdgeCalibration: Calibrated causal strength, propagation delay, provenance, and confidence for edges.
2. CausalExperimentRecord: Tamper-evident audit log of controlled chaos experiments and measured telemetry diffs.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.core.database import Base


class CausalEdgeCalibration(Base):
    """
    Stores experimental causal calibration annotations on dependency edges.
    Preserves declared architecture dependencies while recording experimental evidence.
    """

    __tablename__ = "causal_edge_calibrations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    source_service = Column(String(100), nullable=False, index=True)  # caller
    target_service = Column(String(100), nullable=False, index=True)  # callee

    dependency_type = Column(String(50), nullable=False, default="SYNC")
    causal_strength = Column(Float, nullable=False, default=0.50)  # [0.0, 1.0]
    propagation_delay_ms = Column(Float, nullable=False, default=120.0)
    provenance = Column(String(30), nullable=False, default="DECLARED")  # DECLARED, OBSERVED, VALIDATED_CAUSAL, UNCERTAIN
    confidence = Column(Float, nullable=False, default=0.50)  # [0.0, 1.0]
    repeatability = Column(Float, nullable=False, default=0.50)  # [0.0, 1.0]
    experiment_count = Column(Integer, nullable=False, default=0)
    is_declared = Column(Boolean, nullable=False, default=True)

    did_effect_size = Column(Float, nullable=False, default=0.0)
    p_value_estimate = Column(Float, nullable=False, default=0.05)
    evidence_summary = Column(Text, nullable=True)
    historical_effect_sizes = Column(JSONB, nullable=False, default=list)
    metadata_json = Column(JSONB, nullable=True)

    last_calibrated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "source_service",
            "target_service",
            name="uq_causal_edge_source_target",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CausalEdgeCalibration({self.source_service} -> {self.target_service} "
            f"strength={self.causal_strength:.2f} prov={self.provenance} n={self.experiment_count})>"
        )


class CausalExperimentRecord(Base):
    """
    Audit log of every controlled chaos injection experiment,
    capturing pre-injection baseline, treatment shock, recovery, and neighbor impacts.
    """

    __tablename__ = "causal_experiment_records"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    experiment_id = Column(String(100), unique=True, nullable=False, index=True)
    target_service = Column(String(100), nullable=False, index=True)
    control_service = Column(String(100), nullable=False, default="auth-service")
    fault_type = Column(String(50), nullable=False, default="latency")
    intensity = Column(Float, nullable=False, default=0.8)
    duration_seconds = Column(Integer, nullable=False, default=30)
    environment = Column(String(50), nullable=False, default="demo")
    status = Column(String(30), nullable=False, default="COMPLETED")  # RUNNING, RESTORED, COMPLETED, FAILED

    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=False)
    duration_elapsed_seconds = Column(Float, nullable=False, default=0.0)

    injected_by = Column(String(100), nullable=True)
    baseline_metrics = Column(JSONB, nullable=False, default=dict)
    treatment_metrics = Column(JSONB, nullable=False, default=dict)
    recovery_metrics = Column(JSONB, nullable=False, default=dict)
    observed_impacts = Column(JSONB, nullable=False, default=list)
    safety_audit = Column(JSONB, nullable=False, default=dict)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<CausalExperimentRecord(id={self.experiment_id} target={self.target_service} status={self.status})>"
