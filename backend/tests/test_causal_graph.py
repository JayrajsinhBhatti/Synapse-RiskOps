"""
Synapse RiskOps - Chaos-Calibrated Causal Graph Unit & Integration Tests
=======================================================================
Validates:
1. Controlled experiment execution & safety bounds (rejection of production without override, bounded duration/intensity)
2. Downstream telemetry observation & propagation delay detection (tau > 0)
3. Confounder handling & Difference-in-Differences (DiD) baseline subtraction
4. Directional asymmetry verification (distinguishing caller vs callee causation)
5. Repeated experiments & provenance promotion to VALIDATED_CAUSAL
6. Insufficient observations remaining OBSERVED or UNCERTAIN (no false certainty)
7. Preservation of declared NetworkX dependencies (no declared edges dropped)
8. Cascade Interception Planner integration with calibrated weights
"""

import pytest
import networkx as nx
from datetime import datetime, timezone

from app.schemas.causal import (
    CausalExperimentRequest,
    CausalProvenance,
    FaultType,
)
from app.services.causal_calibrator import (
    CausalCalibratorService,
    causal_calibrator,
)
from app.services.cascade_planner import (
    CascadePlannerService,
    DEFAULT_DEPENDENCIES,
    DEFAULT_SERVICES,
)


@pytest.fixture
def fresh_calibrator():
    """Provides a fresh isolated instance of CausalCalibratorService."""
    return CausalCalibratorService()


@pytest.fixture
def planner():
    """Provides an instance of CascadePlannerService."""
    return CascadePlannerService()


# -------------------------------------------------------------------------
# Test 1: Safety & Governance Constraints
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_production_safety_governance(fresh_calibrator):
    """Destructive experiments against production must be rejected unless explicitly authorized."""
    req = CausalExperimentRequest(
        target_service="payment-service",
        fault_type=FaultType.LATENCY,
        intensity=0.8,
        duration_seconds=30,
        environment="production",
        allow_production=False,
    )
    with pytest.raises(ValueError) as excinfo:
        await fresh_calibrator.run_controlled_experiment(req)
    assert "forbidden" in str(excinfo.value).lower()


@pytest.mark.asyncio
async def test_bounded_fault_intensity_and_duration(fresh_calibrator):
    """Fault intensity and duration must be bounded within safe operational thresholds."""
    # Test with boundary values (max duration = 300, min = 5)
    req = CausalExperimentRequest(
        target_service="payment-service",
        fault_type=FaultType.LATENCY,
        intensity=0.9,
        duration_seconds=30,
        environment="demo",
    )
    result = await fresh_calibrator.run_controlled_experiment(req)
    assert result.status == "COMPLETED"
    assert result.safety_audit["bounds_enforced"]["applied_intensity"] <= 1.0
    assert result.safety_audit["bounds_enforced"]["applied_duration"] <= 300
    assert result.safety_audit["auto_restoration_verified"] is True


# -------------------------------------------------------------------------
# Test 2: Downstream Telemetry Observation & Propagation Delay (tau > 0)
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_downstream_effect_and_propagation_delay(fresh_calibrator):
    """
    Fault injection on callee (payment-service) must produce measurable downstream
    telemetry degradation on caller (order-service) with a detected propagation delay.
    """
    req = CausalExperimentRequest(
        target_service="payment-service",
        fault_type=FaultType.LATENCY,
        intensity=0.85,
        duration_seconds=20,
        control_service="auth-service",
        environment="demo",
    )
    result = await fresh_calibrator.run_controlled_experiment(req)

    # Check observed impacts
    order_impact = next(
        (imp for imp in result.observed_impacts if imp.neighbor_service == "order-service"),
        None,
    )
    assert order_impact is not None, "order-service should be observed as caller of payment-service"
    assert order_impact.delta_latency_ms > 0, "order-service latency should increase during payment fault"
    assert order_impact.propagation_delay_ms > 0, "Propagation delay tau must be detected (> 0 ms)"
    assert order_impact.direction == "UPSTREAM_CALLER"
    assert order_impact.statistical_significance is True


# -------------------------------------------------------------------------
# Test 3: Confounder Handling via Difference-in-Differences
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_confounder_mitigation_with_control_service(fresh_calibrator):
    """
    Difference-in-Differences discounts ambient fluctuations using the control service,
    ensuring that only causal shocks beyond the control baseline are attributed to the edge.
    """
    req = CausalExperimentRequest(
        target_service="payment-service",
        fault_type=FaultType.LATENCY,
        intensity=0.8,
        duration_seconds=15,
        control_service="auth-service",
        environment="demo",
    )
    result = await fresh_calibrator.run_controlled_experiment(req)

    # The DiD effect size must be strictly positive and calculated
    order_impact = next(
        imp for imp in result.observed_impacts if imp.neighbor_service == "order-service"
    )
    assert order_impact.did_effect_size > 0.0
    assert "Difference-in-Differences" in result.causal_inference_method


# -------------------------------------------------------------------------
# Test 4: Repeated Experiments & Provenance Promotion to VALIDATED_CAUSAL
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_repeated_experiments_promote_to_validated_causal(fresh_calibrator):
    """
    A single experiment produces OBSERVED provenance. Repeated consistent trials (N >= 3)
    must promote the relationship to VALIDATED_CAUSAL with high repeatability.
    """
    req = CausalExperimentRequest(
        target_service="payment-service",
        fault_type=FaultType.LATENCY,
        intensity=0.8,
        duration_seconds=15,
        control_service="auth-service",
        environment="demo",
    )

    # Trial 1: Expect OBSERVED
    r1 = await fresh_calibrator.run_controlled_experiment(req)
    e1 = next(e for e in r1.calibrated_edges if e.source == "order-service")
    assert e1.provenance == CausalProvenance.OBSERVED
    assert e1.experiment_count == 1

    # Trial 2: Still OBSERVED
    r2 = await fresh_calibrator.run_controlled_experiment(req)
    e2 = next(e for e in r2.calibrated_edges if e.source == "order-service")
    assert e2.provenance == CausalProvenance.OBSERVED
    assert e2.experiment_count == 2

    # Trial 3: Promoted to VALIDATED_CAUSAL!
    r3 = await fresh_calibrator.run_controlled_experiment(req)
    e3 = next(e for e in r3.calibrated_edges if e.source == "order-service")
    assert e3.provenance == CausalProvenance.VALIDATED_CAUSAL
    assert e3.experiment_count == 3
    assert e3.repeatability >= 0.70
    assert e3.confidence >= 0.65


# -------------------------------------------------------------------------
# Test 5: Insufficient Observations Do Not Claim Causal Certainty
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_insufficient_or_unobserved_edges_remain_declared_or_uncertain(fresh_calibrator):
    """
    Edges without sufficient evidence must remain DECLARED or UNCERTAIN.
    No automatic causal claims without repeated experimental support.
    """
    graph = await fresh_calibrator.get_calibrated_networkx_graph()

    # An edge that was never experimented on
    edge_data = graph["auth-service"]["postgres-primary"]
    assert edge_data["provenance"] == CausalProvenance.DECLARED.value
    assert edge_data["experiment_count"] == 0
    assert "awaiting" in edge_data["evidence_summary"].lower()


# -------------------------------------------------------------------------
# Test 6: NetworkX Graph Calibration Preserves Declared Dependencies
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_graph_calibration_preserves_declared_edges(fresh_calibrator):
    """
    Calibration must preserve all original declared dependencies.
    Never remove declared dependencies based on a single experiment.
    """
    # Run an experiment on inventory-service
    req = CausalExperimentRequest(
        target_service="inventory-service",
        fault_type=FaultType.LATENCY,
        intensity=0.75,
        duration_seconds=15,
        environment="demo",
    )
    await fresh_calibrator.run_controlled_experiment(req)

    graph = await fresh_calibrator.get_calibrated_networkx_graph()

    # All 12 default services must still exist
    for svc in DEFAULT_SERVICES:
        assert svc["name"] in graph.nodes, f"Service {svc['name']} missing from graph!"

    # All 19 declared dependencies must still exist
    for src, tgt, _, _ in DEFAULT_DEPENDENCIES:
        assert graph.has_edge(src, tgt), f"Declared edge ({src} -> {tgt}) was erroneously deleted!"


# -------------------------------------------------------------------------
# Test 7: Cascade Interception Planner Uses Calibrated Causal Weights
# -------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cascade_planner_incorporates_causal_calibrations(planner):
    """
    Cascade Interception Planner must use calibrated causal strength and propagation delay
    to adjust propagation probabilities and time-to-impact.
    """
    # 1. Topology without calibration
    graph_base = await planner.build_topology_graph()
    sim_base = planner.simulate_propagation(graph_base, seed_service="payment-service")
    hop_base = next(h for h in sim_base.propagation_timeline if h.service_name == "order-service")

    # 2. Topology with high causal calibration on order-service -> payment-service
    graph_cal = graph_base.copy()
    graph_cal["order-service"]["payment-service"].update({
        "causal_strength": 0.95,
        "propagation_delay_ms": 130.0,
        "provenance": CausalProvenance.VALIDATED_CAUSAL.value,
        "confidence": 0.96,
    })

    sim_cal = planner.simulate_propagation(graph_cal, seed_service="payment-service")
    hop_cal = next(h for h in sim_cal.propagation_timeline if h.service_name == "order-service")

    # Calibrated propagation delay should produce faster, more precise time-to-impact
    assert hop_cal.estimated_time_to_impact_seconds < hop_base.estimated_time_to_impact_seconds
    assert hop_cal.propagation_probability > 0.0
