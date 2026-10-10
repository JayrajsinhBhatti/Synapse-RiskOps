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
