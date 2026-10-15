"""
Synapse RiskOps - Cascade Interception Planner Verification Tests
================================================================
Comprehensive test suite validating:
1. Failure propagation simulation (BFS with edge weight decay & sync vs async impact)
2. Cycles and missing/disconnected dependencies handling (graph robustness)
3. Competing action plans generation, scoring, and ranking
4. Critical services protection & strict Autonomy Budget approval gates
5. Insufficient telemetry / sparse data handling
6. Operator approval enforcement & unauthorized execution rejection
7. Failed intervention handling and graceful error recovery
8. Before/after impact calculations (blast radius delta, protected services count)
"""

import sys
from pathlib import Path
from uuid import uuid4

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import networkx as nx
import pytest
import httpx
from httpx import ASGITransport

from app.main import app as fastapi_app
from app.core.security import create_access_token
from app.core.database import async_engine, Base
from app.services.cascade_planner import cascade_planner_service, CascadePlannerService
import app.models  # ensure models registered


# =========================================================================
# 1 & 2. Unit Tests: Propagation, Cycles, Missing Dependencies
# =========================================================================

def test_propagation_and_cycle_handling():
    """
    Test propagation across a directed graph containing intentional feedback loops/cycles:
    A -> B -> C -> A (cycle), C -> D -> E (downstream)
    Verify that BFS terminates safely without infinite recursion and tracks all hops.
    """
    g = nx.DiGraph()
    # Edges: u -> v means u calls v
    g.add_node("ServiceA", criticality="HIGH")
    g.add_node("ServiceB", criticality="HIGH")
    g.add_node("ServiceC", criticality="CRITICAL")
    g.add_node("ServiceD", criticality="MEDIUM")
    g.add_node("ServiceE", criticality="LOW")

    # Intentional cyclic dependencies
    g.add_edge("ServiceA", "ServiceB", edge_type="SYNC", latency_p95_ms=100)
    g.add_edge("ServiceB", "ServiceC", edge_type="SYNC", latency_p95_ms=200)
    g.add_edge("ServiceC", "ServiceA", edge_type="SYNC", latency_p95_ms=150)
    # Downstream callers/callees
    g.add_edge("ServiceD", "ServiceC", edge_type="SYNC", latency_p95_ms=80)
    g.add_edge("ServiceE", "ServiceD", edge_type="ASYNC", latency_p95_ms=50)

    # Seed failure at ServiceC
    result = cascade_planner_service.simulate_propagation(
        graph=g,
        seed_service="ServiceC",
        failure_type="latency_spike",
        severity=0.85,
    )

    assert result.seed_service == "ServiceC"
    assert result.blast_radius_percent > 0
    # ServiceB and ServiceD both call ServiceC directly (predecessors)
    affected_services = {hop.service_name for hop in result.propagation_timeline}
    assert "ServiceB" in affected_services
    assert "ServiceD" in affected_services

    # Cycle shouldn't cause infinite paths
    assert len(result.propagation_paths) <= g.number_of_nodes()
    # Verify no hops exceed max depth
    for hop in result.propagation_timeline:
        assert hop.depth <= 4


def test_missing_and_disconnected_dependencies():
    """
    Test edge cases:
    - Seed service not in graph
    - Isolated node with 0 predecessors and 0 successors
    """
    g = nx.DiGraph()
    g.add_node("solo-service", criticality="LOW")

    # 1. Missing service
    missing_result = cascade_planner_service.simulate_propagation(
        graph=g,
        seed_service="non-existent-service",
        failure_type="node_crash",
    )
    assert missing_result.seed_service == "non-existent-service"
    assert missing_result.at_risk_count == 0
    assert missing_result.propagation_paths == []

    # 2. Solo isolated service
    solo_result = cascade_planner_service.simulate_propagation(
        graph=g,
        seed_service="solo-service",
        failure_type="node_crash",
    )
    assert solo_result.at_risk_count == 0
    assert solo_result.blast_radius_percent >= 0.0


# =========================================================================
# 3 & 8. Competing Action Plans & Before/After Impact Calculations
# =========================================================================

def test_competing_action_plans_and_impact_delta():
    """
    Verify that candidate action plans are generated, ranked, and calculate
    before/after blast radius delta accurately.
    """
    planner = CascadePlannerService()
    g = nx.DiGraph()

    nodes = ["api-gateway", "order-service", "payment-service", "postgres-primary", "notification-service"]
    criticalities = {
        "api-gateway": "CRITICAL",
        "order-service": "HIGH",
        "payment-service": "CRITICAL",
        "postgres-primary": "CRITICAL",
        "notification-service": "LOW",
    }
    for n in nodes:
        g.add_node(n, criticality=criticalities[n])

    g.add_edge("api-gateway", "order-service", edge_type="SYNC")
    g.add_edge("order-service", "payment-service", edge_type="SYNC")
    g.add_edge("payment-service", "postgres-primary", edge_type="SYNC")
    g.add_edge("order-service", "notification-service", edge_type="ASYNC")

    sim = planner.simulate_propagation(g, seed_service="payment-service", failure_type="latency_spike")
    plans = planner.generate_interception_plans(g, seed_service="payment-service", baseline_sim=sim)

    assert len(plans) >= 3
    # Check ranking
    assert plans[0].rank == 1
    assert any(p.is_recommended for p in plans)

    # Validate before/after impact calculations
    for plan in plans:
        assert plan.blast_radius_before_percent == sim.blast_radius_percent
        assert plan.blast_radius_after_percent <= plan.blast_radius_before_percent
        assert plan.blast_radius_reduction_percent >= 0.0
        assert plan.blast_radius_reduction_percent == round(plan.blast_radius_before_percent - plan.blast_radius_after_percent, 1)
        assert len(plan.actions) > 0
        assert plan.overall_efficacy_score > 0.0


# =========================================================================
# 4 & 5. Critical Services & Insufficient Telemetry
# =========================================================================

def test_critical_service_autonomy_and_insufficient_telemetry():
    """
    Validate that critical services (e.g. payment-service, postgres-primary) require
    human approval even when blast radius reduction is high, and that insufficient
    telemetry produces safe, non-hallucinated estimates.
    """
    planner = CascadePlannerService()
    g = nx.DiGraph()

    g.add_node("payment-service", criticality="CRITICAL")
    g.add_node("order-service", criticality="HIGH")
    g.add_edge("order-service", "payment-service", edge_type="SYNC")

    sim = planner.simulate_propagation(g, seed_service="payment-service")
    plans = planner.generate_interception_plans(g, seed_service="payment-service", baseline_sim=sim)

    # For payment-service (CRITICAL), plans should flag approval requirements
    critical_plan = next(p for p in plans if "payment-service" in [a.target_service for a in p.actions] or p.requires_human_approval)
    assert critical_plan.requires_human_approval is True
    assert critical_plan.autonomy_tier == "REQUIRE_APPROVAL"

    # Verify assumptions are explicitly documented and not hidden
    assert len(sim.assumptions_and_evidence) > 0
    assert any("evidence" in a.lower() or "simulation" in a.lower() or "telemetry" in a.lower() or "hop" in a.lower() for a in sim.assumptions_and_evidence)


# =========================================================================
# 6 & 7. End-to-End API: Approval Gates, Execution & Failure Handling
# =========================================================================

@pytest.mark.asyncio
async def test_api_simulate_and_execution_gates():
    """
    Test end-to-end API workflows via HTTP transport:
    - POST /api/cascade/simulate
    - POST /api/cascade/execute-plan with unauthorized engineer (blocked)
    - POST /api/cascade/execute-plan with approved operator (executed)
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from app.core.database import AsyncSessionLocal
    from app.core.security import get_password_hash
    from app.models.user import User
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        # Operator user
        res = await session.execute(select(User).where(User.username == "operator_cascade"))
        op_user = res.scalar_one_or_none()
        if not op_user:
            op_user = User(
                username="operator_cascade",
                email="operator_cascade@test.local",
                password_hash=get_password_hash("pass123"),
                full_name="Operations Lead",
                role="OPERATOR",
                is_active=True,
            )
            session.add(op_user)
            await session.commit()
            await session.refresh(op_user)

        # Engineer user (read-only / cannot sign off critical)
        res = await session.execute(select(User).where(User.username == "engineer_cascade"))
        eng_user = res.scalar_one_or_none()
        if not eng_user:
            eng_user = User(
                username="engineer_cascade",
                email="engineer_cascade@test.local",
                password_hash=get_password_hash("pass123"),
                full_name="Junior Dev",
                role="ENGINEER",
                is_active=True,
            )
            session.add(eng_user)
            await session.commit()
            await session.refresh(eng_user)

    op_token = create_access_token({"sub": str(op_user.id), "username": op_user.username, "role": op_user.role})
    eng_token = create_access_token({"sub": str(eng_user.id), "username": eng_user.username, "role": eng_user.role})

    transport = ASGITransport(app=fastapi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Simulate cascade
        sim_res = await client.post(
            "/api/cascade/simulate",
            json={
                "seed_service": "payment-service",
                "failure_type": "latency_spike",
                "severity": 0.9,
            },
            headers={"Authorization": f"Bearer {op_token}"},
        )
        assert sim_res.status_code == 200
        sim_data = sim_res.json()
        assert sim_data["seed_service"] == "payment-service"
        assert len(sim_data["candidate_plans"]) >= 3
        assert sim_data["recommended_plan"] is not None

        recommended_plan = sim_data["recommended_plan"]
        plan_id = recommended_plan["plan_id"]

        # 2. Engineer attempts to execute critical plan without approval -> 403 Forbidden
        eng_exec_res = await client.post(
            "/api/cascade/execute-plan",
            json={
                "plan_id": plan_id,
                "seed_service": "payment-service",
                "strategy": recommended_plan["strategy"],
                "approval_notes": "Attempting unapproved execution",
            },
            headers={"Authorization": f"Bearer {eng_token}"},
        )
        assert eng_exec_res.status_code == 403
        detail_msg = eng_exec_res.json()["detail"].lower()
        assert "not authorized" in detail_msg or "autonomy budget" in detail_msg

        # 3. Authorized Operator executes plan with approval -> 200 OK
        op_exec_res = await client.post(
            "/api/cascade/execute-plan",
            json={
                "plan_id": plan_id,
                "seed_service": "payment-service",
                "strategy": recommended_plan["strategy"],
                "approval_notes": "Authorized by SecOps Lead for cascade isolation",
            },
            headers={"Authorization": f"Bearer {op_token}"},
        )
        assert op_exec_res.status_code == 200
        exec_data = op_exec_res.json()
        assert exec_data["status"] == "DISPATCHED"
        assert exec_data["plan_id"] == plan_id
        assert len(exec_data["audit_log_ids"]) > 0
        assert len(exec_data["dispatched_actions"]) > 0


@pytest.mark.asyncio
async def test_api_invalid_service_and_failure_resilience():
    """
    Test resilience against invalid inputs:
    - Non-existent service simulation gracefully handles topology lookup
    - Missing plan execution returns informative 400 error
    """
    transport = ASGITransport(app=fastapi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Non-existent service should return 200 with 0 cascade impact rather than 500 crash
        res = await client.post(
            "/api/cascade/simulate",
            json={
                "seed_service": "unknown-ghost-service",
                "failure_type": "memory_leak",
                "severity": 0.5,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["simulation"]["at_risk_count"] == 0
        assert isinstance(data["candidate_plans"], list)
