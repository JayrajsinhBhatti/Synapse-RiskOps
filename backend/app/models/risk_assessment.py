"""
Synapse RiskOps - Risk Assessment ORM Model
===========================================
Owner: Person 2 | Week: 5

Maps to `risk_assessments` table in docker/postgres/init.sql.
Stores historical snapshots of ML RiskEngine predictions for evaluation and auditing.
"""

import uuid
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TEXT, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class RiskAssessment(Base):
    """Historical risk assessment evaluated by the ML Engine."""

    __tablename__ = "risk_assessments"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    service_id = Column(
        UUID(as_uuid=True),
        ForeignKey("services.id"),
        nullable=False,
        index=True,
    )

    risk_score = Column(Numeric(5, 2), nullable=False)
    confidence = Column(Numeric(5, 4), nullable=False)
    anomaly_score = Column(Numeric(10, 6), nullable=True)
    predicted_failure_time = Column(DateTime(timezone=True), nullable=True)

    affected_services = Column(ARRAY(TEXT), nullable=True)
    features_used = Column(JSONB, nullable=True)
    model_version = Column(String(50), nullable=True)

    assessed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    service = relationship("Service")

    def __repr__(self) -> str:
        return f"<RiskAssessment(service_id='{self.service_id}', score={self.risk_score}, at='{self.assessed_at}')>"
