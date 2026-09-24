"""
Synapse RiskOps - Incident & Incident History ORM Models
========================================================
Owner: Person 2 | Week: 5

Maps to `incidents` and `incident_history` tables in docker/postgres/init.sql.
Matches the shared schema contract in shared/schemas/incident_record.schema.json.
"""

import uuid
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Incident(Base):
    """Main incident record for tracking outages, risks, and autonomous resolutions."""

    __tablename__ = "incidents"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False, default="MEDIUM", index=True)
    status = Column(String(20), nullable=False, default="OPEN", index=True)

    service_id = Column(
        UUID(as_uuid=True),
        ForeignKey("services.id"),
        nullable=True,
        index=True,
    )

    risk_score = Column(Numeric(5, 2), nullable=True)
    confidence = Column(Numeric(5, 4), nullable=True)
    predicted_failure = Column(DateTime(timezone=True), nullable=True)

    detected_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    assigned_to = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
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

    # Relationships
    service = relationship("Service", back_populates="incidents")
    assignee = relationship("User", foreign_keys=[assigned_to])
    creator = relationship("User", foreign_keys=[created_by])
    history = relationship(
        "IncidentHistory",
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="IncidentHistory.changed_at.desc()",
    )

    def __repr__(self) -> str:
        return f"<Incident(id='{self.id}', title='{self.title}', status='{self.status}', severity='{self.severity}')>"


class IncidentHistory(Base):
    """Audit trail tracking incident mutations, human overrides, and automated actions."""

    __tablename__ = "incident_history"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    incident_id = Column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action = Column(String(50), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)

    changed_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    changed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    incident = relationship("Incident", back_populates="history")
    author = relationship("User", foreign_keys=[changed_by])

    def __repr__(self) -> str:
        return f"<IncidentHistory(incident_id='{self.incident_id}', action='{self.action}', at='{self.changed_at}')>"
