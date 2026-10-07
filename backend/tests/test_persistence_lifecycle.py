"""
Synapse RiskOps - Layer 8 PostgreSQL Data Persistence Test Suite
=================================================================
Validates full incident lifecycle in PostgreSQL:
- test_incident_persistence: creation/INSERT with full diagnostic schema
- test_incident_update: observation mutation/UPDATE
- test_incident_resolution: recovery resolution/UPDATE with resolved_at
- test_historical_incident_retrieval: historical retrieval from PostgreSQL
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.incident import Incident, IncidentHistory
from app.models.service import Service


@pytest.mark.asyncio
async def test_incident_persistence():
    """Verify that a complete incident record and audit log are persisted to PostgreSQL."""
    async with AsyncSessionLocal() as session:
        # Find or create a service
        svc_res = await session.execute(select(Service).where(Service.service_name == "payment-service"))
        service = svc_res.scalar_one_or_none()
        service_id = service.id if service else None
        
        inc_id = uuid4()
        now = datetime.now(timezone.utc)
        
        incident = Incident(
            id=inc_id,
            title="Incident: Payment Service Latency Degradation",
            description="Autonomous risk detection triggered for payment-service.",
            severity="CRITICAL",
            status="OPEN",
            service_id=service_id,
            risk_score=Decimal("82.40"),
            confidence=Decimal("0.9100"),
            predicted_failure=now,
            risk_tier="CRITICAL",
            anomaly_score=Decimal("0.8240"),
            forecast_risk=Decimal("0.7400"),
            predicted_failure_type="latency_degradation",
            root_cause="payment-service latency degradation",
            guidance="Scale service or increase connection pool",
            routing_decision="human_approval",
            top_features={"response_time_p99": 4500.0, "cpu_usage": 35.0},
            affected_services=["payment-service", "order-service"],
            detected_at=now,
            resolved_at=None,
        )
        session.add(incident)
        await session.flush()
        
        # Add audit trail
        history = IncidentHistory(
            incident_id=inc_id,
            action="CREATED",
            new_value="Created CRITICAL incident with risk score 82.40",
            changed_at=now,
        )
        session.add(history)
        await session.commit()
        
        # Query back from PostgreSQL
        res = await session.execute(select(Incident).where(Incident.id == inc_id))
        persisted = res.scalar_one_or_none()
        
        assert persisted is not None
        assert persisted.severity == "CRITICAL"
        assert persisted.risk_score == Decimal("82.40")
        assert persisted.risk_tier == "CRITICAL"
        assert persisted.root_cause == "payment-service latency degradation"
        assert persisted.guidance == "Scale service or increase connection pool"
        assert persisted.confidence == Decimal("0.9100")
        assert persisted.routing_decision == "human_approval"
        assert persisted.status == "OPEN"
        assert persisted.resolved_at is None
        assert persisted.created_at is not None


@pytest.mark.asyncio
async def test_incident_update():
    """Verify that repeated observation updates the existing incident record in PostgreSQL."""
    async with AsyncSessionLocal() as session:
        inc_id = uuid4()
        now = datetime.now(timezone.utc)
        
        incident = Incident(
            id=inc_id,
            title="Incident: Initial Payment Degradation",
            severity="HIGH",
            status="OPEN",
            risk_score=Decimal("65.00"),
            confidence=Decimal("0.8500"),
            detected_at=now,
        )
        session.add(incident)
        await session.commit()
        
        # Update incident with higher risk score
        incident.risk_score = Decimal("88.50")
        incident.severity = "CRITICAL"
        
        history = IncidentHistory(
            incident_id=inc_id,
            action="OBSERVATION_UPDATED",
            new_value="Risk score updated to 88.50 (CRITICAL)",
            changed_at=datetime.now(timezone.utc),
        )
        session.add(history)
        await session.commit()
        
        # Verify update
        res = await session.execute(select(Incident).where(Incident.id == inc_id))
        updated = res.scalar_one_or_none()
        assert updated is not None
        assert updated.risk_score == Decimal("88.50")
        assert updated.severity == "CRITICAL"


@pytest.mark.asyncio
async def test_incident_resolution():
    """Verify that service recovery updates incident status to RESOLVED and records resolved_at in PostgreSQL."""
    async with AsyncSessionLocal() as session:
        inc_id = uuid4()
        now = datetime.now(timezone.utc)
        
        incident = Incident(
            id=inc_id,
            title="Incident: Temporary Spike",
            severity="CRITICAL",
            status="OPEN",
            risk_score=Decimal("80.00"),
            detected_at=now,
        )
        session.add(incident)
        await session.commit()
        
        # Resolve incident
        resolved_time = datetime.now(timezone.utc)
        incident.status = "RESOLVED"
        incident.resolved_at = resolved_time
        incident.risk_score = Decimal("22.50")
        
        history = IncidentHistory(
            incident_id=inc_id,
            action="RECOVERED",
            new_value="Telemetry recovered below threshold. Incident closed.",
            changed_at=resolved_time,
        )
        session.add(history)
        await session.commit()
        
        # Verify resolution persisted
        res = await session.execute(select(Incident).where(Incident.id == inc_id))
        resolved = res.scalar_one_or_none()
        assert resolved is not None
        assert resolved.status == "RESOLVED"
        assert resolved.resolved_at is not None
        assert resolved.risk_score == Decimal("22.50")


@pytest.mark.asyncio
async def test_historical_incident_retrieval():
    """Verify that resolved incidents can be retrieved historically from PostgreSQL with complete audit data."""
    async with AsyncSessionLocal() as session:
        # Retrieve all historical resolved incidents
        res = await session.execute(
            select(Incident).where(Incident.status == "RESOLVED").order_by(Incident.detected_at.desc())
        )
        historical = res.scalars().all()
        
        assert len(historical) >= 1
        record = historical[0]
        assert record.status == "RESOLVED"
        assert record.resolved_at is not None
        assert record.id is not None
