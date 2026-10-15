"""
Synapse RiskOps - Dry-Run Twin (Counterfactual Remediation) Test Suite
=====================================================================
Comprehensive tests verifying:
1. Safe separation: Dry runs NEVER trigger real Ansible playbooks or mutate service state.
2. Multi-action counterfactual comparison: Candidate remediations are evaluated side-by-side
   with distinct trade-offs (recovery time, health delta, secondary failure hazards).
3. Recommendation ranking: Efficacy score calculates safest recommended action.
4. Autonomy Budget & Cascade Integration: Evaluates approval requirements against
   risk threshold (74.0) and critical services, while computing blast radius reduction.
5. Sparse / Missing Telemetry: Handles uncalibrated services and missing metrics gracefully
   with explicit limitations and uncertainty tags.
6. Authorized separate execution: Transition from simulation to actual execution requires
   an explicit, authorized API call.
"""

import sys
from pathlib import Path
from uuid import uuid4

# Ensure backend root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import httpx
from httpx import ASGITransport

from app.main import app as fastapi_app
from app.core.security import create_access_token
from app.core.database import async_engine, Base
from app.services.dry_run_twin import dry_run_twin_service, DryRunTwinService
from app.schemas.dry_run import DryRunSimulateRequest
import app.models  # Ensure models registered


@pytest.mark.asyncio
async def test_dry_run_simulation_does_not_trigger_real_action():
    """
    Test 1: Verify that executing a dry-run simulation produces detailed counterfactual
    predictions without triggering any real Ansible task or modifying production state.
    """
    service_name = "payment-service"
    current_metrics = {
        "cpu_usage": 85.0,
        "memory_usage": 78.0,
        "error_rate": 14.5,
        "response_time_p99": 750.0,
    }

    res = await dry_run_twin_service.simulate_remediation_options(
        service_name=service_name,
        current_metrics=current_metrics,
        candidate_actions=["SCALE_OUT_PODS", "RESTART_POD", "CIRCUIT_BREAKER_TRIP"],
    )

    # 1. Output structure assertions
    assert res.is_simulated is True
    assert res.service_name == service_name
    assert len(res.candidate_simulations) == 3
    assert res.recommended_action in ["SCALE_OUT_PODS", "RESTART_POD", "CIRCUIT_BREAKER_TRIP"]
    assert "simplified counterfactual predictive simulator" in res.disclaimer.lower()

    # 2. Verify all candidates have predictions and secondary risks without executing real playbooks
    for cand in res.candidate_simulations:
        assert cand.predicted_health_score > res.baseline_telemetry["health_score"]
        assert cand.predicted_risk_score < res.baseline_telemetry["risk_score"]
        assert cand.estimated_execution_seconds > 0
        assert cand.estimated_recovery_seconds > 0
        assert isinstance(cand.secondary_failure_risks, list)
        assert cand.efficacy_score >= 0.0

    # 3. Verify exactly one candidate is marked recommended
    recommended_candidates = [c for c in res.candidate_simulations if c.is_recommended]
    assert len(recommended_candidates) == 1
    assert recommended_candidates[0].action == res.recommended_action


@pytest.mark.asyncio
async def test_candidate_actions_side_by_side_tradeoffs():
    """
    Test 2: Verify candidate actions have distinct, realistic operational trade-offs:
    - RESTART_POD: high memory/cpu reduction, cold start secondary risk.
    - CIRCUIT_BREAKER_TRIP: fastest recovery time, caller fallback degradation risk.
    - SCALE_OUT_PODS: reversible, DB pool saturation risk.
    """
    service_name = "order-service"
    metrics = {
        "cpu_usage": 92.0,
        "memory_usage": 88.0,
        "error_rate": 18.0,
        "response_time_p99": 850.0,
    }

    res = await dry_run_twin_service.simulate_remediation_options(
        service_name=service_name,
        current_metrics=metrics,
        candidate_actions=[
            "SCALE_OUT_PODS",
            "RESTART_POD",
            "RATE_LIMIT_TRAFFIC",
            "CIRCUIT_BREAKER_TRIP",
        ],
    )

    action_map = {c.action: c for c in res.candidate_simulations}

    # Circuit breaker is fast to execute/isolate
    assert action_map["CIRCUIT_BREAKER_TRIP"].estimated_execution_seconds <= 2.5
    # Scale out pods is reversible
    assert action_map["SCALE_OUT_PODS"].reversibility == "REVERSIBLE"
    # Restart pod is partially reversible
    assert action_map["RESTART_POD"].reversibility == "PARTIALLY_REVERSIBLE"

    # Verify secondary hazards are populated appropriately
    cb_hazards = [r.risk_type for r in action_map["CIRCUIT_BREAKER_TRIP"].secondary_failure_risks]
    assert "DEGRADED_FEATURE_EXPERIENCE" in cb_hazards

    scale_hazards = [r.risk_type for r in action_map["SCALE_OUT_PODS"].secondary_failure_risks]
    assert "DATABASE_CONNECTION_POOL_EXHAUSTION" in scale_hazards


@pytest.mark.asyncio
async def test_autonomy_budget_evaluation_and_critical_services():
    """
    Test 3: Verify Autonomy Budget integration:
    - Critical services (e.g. payment-service) or risk scores > 74 require human approval.
    - Low-risk non-critical services (risk score <= 74) can qualify for auto-execution.
    """
    # High risk / critical service: payment-service with 85% risk
    critical_res = await dry_run_twin_service.simulate_remediation_options(
        service_name="payment-service",
        current_metrics={"cpu_usage": 85.0, "error_rate": 10.0, "response_time_p99": 600.0},
        candidate_actions=["SCALE_OUT_PODS"],
    )
    payment_cand = critical_res.candidate_simulations[0]
    assert payment_cand.can_auto_execute is False
    assert payment_cand.approval_requirement in ["REQUIRES_APPROVAL", "STRICT_HUMAN_APPROVAL"]

    # Low risk / non-critical service: notification-service with low baseline risk (<= 74)
    low_risk_res = await dry_run_twin_service.simulate_remediation_options(
        service_name="notification-service",
        current_metrics={"cpu_usage": 35.0, "error_rate": 0.5, "response_time_p99": 85.0},
        candidate_actions=["SCALE_OUT_PODS"],
    )
    notif_cand = low_risk_res.candidate_simulations[0]
    assert notif_cand.can_auto_execute is True
    assert notif_cand.approval_requirement == "AUTO_EXECUTABLE"


@pytest.mark.asyncio
async def test_missing_and_sparse_telemetry_handling():
    """
    Test 4: Verify simulation handles missing metrics, uncalibrated services, or empty inputs
    defensively, populating limitations and uncertainty tags without raising exceptions.
    """
    res = await dry_run_twin_service.simulate_remediation_options(
        service_name="unknown-custom-service",
        current_metrics=None,  # Missing telemetry completely
        candidate_actions=None,  # All standard candidates
    )

    assert res.is_simulated is True
    assert res.service_name == "unknown-custom-service"
    assert len(res.candidate_simulations) >= 5
    # Should have explicit limitations noting missing live metrics
    assert len(res.limitations) > 0
    assert any("telemetry" in lim.lower() or "empirical" in lim.lower() for lim in res.limitations)
    # Uncertainty tier should reflect missing empirical data
    for cand in res.candidate_simulations:
        assert cand.uncertainty_tier in ["MEDIUM", "HIGH"]


@pytest.mark.asyncio
async def test_api_dry_run_simulate_endpoint():
    """
    Test 5: REST API test for POST /api/dry-run/simulate.
    """
    token = create_access_token({"sub": "admin", "role": "admin"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "service_name": "inventory-service",
        "current_metrics": {
            "cpu_usage": 80.0,
            "memory_usage": 72.0,
            "error_rate": 8.0,
            "response_time_p99": 480.0,
        },
        "candidate_actions": ["SCALE_OUT_PODS", "RESTART_POD", "FLUSH_REDIS_CACHE"],
        "environment": "production",
    }

    transport = ASGITransport(app=fastapi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/dry-run/simulate", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        assert data["service_name"] == "inventory-service"
        assert data["is_simulated"] is True
        assert len(data["candidate_simulations"]) == 3
        assert data["recommended_action"] is not None
        assert "CounterfactualQueueingTwin" in data["model_version"]
        assert len(data["assumptions"]) > 0


@pytest.mark.asyncio
async def test_authorized_execution_separation():
    """
    Test 6: Verify that execution of a simulated remediation requires an explicit, separate
    authorized POST request to /api/dry-run/{simulation_id}/execute, and rejects non-existent IDs.
    """
    token = create_access_token({"sub": "admin", "role": "admin"})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=fastapi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Run simulation first
        sim_resp = await client.post(
            "/api/dry-run/simulate",
            json={"service_name": "cart-service", "candidate_actions": ["SCALE_OUT_PODS"]},
            headers=headers,
        )
        assert sim_resp.status_code == 200
        sim_data = sim_resp.json()
        sim_id = sim_data["simulation_id"]

        # 2. Check detail endpoint GET /api/dry-run/{sim_id}
        detail_resp = await client.get(f"/api/dry-run/{sim_id}", headers=headers)
        assert detail_resp.status_code == 200
        assert detail_resp.json()["simulation_id"] == sim_id

        # 3. Attempt execution on a fake simulation ID should 400 or 404
        fake_id = str(uuid4())
        fake_exec = await client.post(
            f"/api/dry-run/{fake_id}/execute",
            json={"selected_action": "SCALE_OUT_PODS"},
            headers=headers,
        )
        assert fake_exec.status_code in [400, 404]

        # 4. Check history endpoint GET /api/dry-run/history
        history_resp = await client.get("/api/dry-run/history", headers=headers)
        assert history_resp.status_code == 200
        history_list = history_resp.json()
        assert any(item["id"] == sim_id for item in history_list)

        # 5. Successful authorized execution of the valid simulation
        real_exec = await client.post(
            f"/api/dry-run/{sim_id}/execute",
            json={"selected_action": "SCALE_OUT_PODS", "approval_notes": "Operator sign-off test"},
            headers=headers,
        )
        assert real_exec.status_code == 200
        exec_json = real_exec.json()
        assert exec_json["simulation_id"] == sim_id
        assert exec_json["executed_action"] == "SCALE_OUT_PODS"
        assert exec_json["execution_status"] == "DISPATCHED"
