"""
Synapse RiskOps - Service & Dependency ORM Models
=================================================
Owner: Person 2 | Week: 5

Maps to `services` and `service_dependencies` tables in docker/postgres/init.sql.
Synchronizes with the NetworkX dependency graph used in Week 3 & 4.
"""

import uuid
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Service(Base):
    """Microservice or infrastructure component tracked in the architecture."""

    __tablename__ = "services"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    service_name = Column(String(100), unique=True, nullable=False, index=True)
    service_type = Column(String(50), nullable=False, default="MICROSERVICE")
    description = Column(Text, nullable=True)
    owner = Column(String(100), nullable=True)
    criticality = Column(String(20), nullable=False, default="MEDIUM")
    is_active = Column(Boolean, nullable=False, default=True)
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
    incidents = relationship("Incident", back_populates="service")
    outgoing_dependencies = relationship(
        "ServiceDependency",
        foreign_keys="ServiceDependency.source_service_id",
        back_populates="source_service",
        cascade="all, delete-orphan",
    )
    incoming_dependencies = relationship(
        "ServiceDependency",
        foreign_keys="ServiceDependency.target_service_id",
        back_populates="target_service",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Service(name='{self.service_name}', type='{self.service_type}', crit='{self.criticality}')>"


class ServiceDependency(Base):
    """Directed dependency edge between two services."""

    __tablename__ = "service_dependencies"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    source_service_id = Column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_service_id = Column(
        UUID(as_uuid=True),
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dependency_type = Column(String(50), nullable=False, default="SYNC")
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "source_service_id",
            "target_service_id",
            name="uq_service_dependency",
        ),
    )

    # Relationships
    source_service = relationship(
        "Service",
        foreign_keys=[source_service_id],
        back_populates="outgoing_dependencies",
    )
    target_service = relationship(
        "Service",
        foreign_keys=[target_service_id],
        back_populates="incoming_dependencies",
    )

    def __repr__(self) -> str:
        return f"<ServiceDependency({self.source_service_id} -> {self.target_service_id} [{self.dependency_type}])>"
