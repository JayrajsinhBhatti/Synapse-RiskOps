"""
Synapse RiskOps - Data Retention & Workspace Settings ORM Models
================================================================
Provides persistent models for time-based log retention policies
and global workspace runtime configurations.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class RetentionPolicy(Base):
    """
    Time-based retention policy configuration per module.
    Supported retention_period values: '1d', '7d', '30d', '90d', 'all'.
    """

    __tablename__ = "retention_policies"

    module = Column(String(50), primary_key=True)  # 'incidents', 'risk_assessments'
    retention_period = Column(String(20), nullable=False, default="all")
    auto_purge_enabled = Column(Boolean, nullable=False, default=True)
    last_purged_at = Column(DateTime(timezone=True), nullable=True)
    records_purged_last = Column(Integer, default=0)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<RetentionPolicy(module='{self.module}', period='{self.retention_period}')>"


class WorkspaceSetting(Base):
    """
    Global workspace runtime settings (e.g., active data_mode, connection parameters).
    """

    __tablename__ = "workspace_settings"

    key = Column(String(50), primary_key=True)
    value = Column(JSONB, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<WorkspaceSetting(key='{self.key}')>"


class AdminAuditLog(Base):
    """
    Immutable audit trail for sensitive administrative operations,
    including manual operational log clearances and retention adjustments.
    """

    __tablename__ = "admin_audit_logs"

    id = Column(
        String(50),
        primary_key=True,
    )
    action = Column(String(100), nullable=False)
    scope = Column(String(100), nullable=False)
    reason = Column(Text, nullable=False)
    records_affected = Column(Integer, default=0, nullable=False)
    performed_by = Column(String(100), nullable=False)
    performed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    metadata_json = Column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<AdminAuditLog(action='{self.action}', by='{self.performed_by}', affected={self.records_affected})>"
