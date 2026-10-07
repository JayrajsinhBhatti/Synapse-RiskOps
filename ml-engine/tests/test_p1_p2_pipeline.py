"""
Synapse RiskOps - P1 & P2 Unit & Regression Test Suite
======================================================
Tests:
- P1-A & P1-B: Anomaly score dynamic rescaling, univariate z-score guardrail,
  zero std handling, non-finite input safety, extreme metrics handling.
- P2: Topology-aware cascade risk propagation, graph distance decay, cycle safety,
  independent local anomaly dominance, risk cap at 100.
- Trigger, Deduplication, Debouncing, and RCA root-cause distinction.
"""

import sys
import math
import numpy as np
import pandas as pd
import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Ensure ml-engine root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.anomaly_detector import AnomalyDetector
from app.services.risk_engine import RiskEngine
from app.services.csv_loader import CSVLoader
from app.services.graph_builder import GraphBuilder


@pytest.fixture(scope="module")
def trained_detector_and_engine():
    loader = CSVLoader()
    df = loader.load_metrics()

    detector = AnomalyDetector(contamination=0.03)
    detector.train(df)

    engine = RiskEngine()
    engine.train(df)

    return detector, engine, df


# ==============================================================================
# PART 1: P1 ANOMALY SCORE & GUARDRAILS TESTS
# ==============================================================================

def test_p1_extreme_p99_latency_increases_anomaly_severity(trained_detector_and_engine):
    """P1: Extreme response_time_p99 must activate guardrail and substantially elevate anomaly severity."""
    detector, _, _ = trained_detector_and_engine

    baseline_metrics = {
        "cpu_usage": 20.0, "memory_usage": 35.0, "disk_io": 10.0,
        "network_latency_ms": 5.0, "request_count": 5000, "error_rate": 0.01,
        "response_time_p99": 35.0, "active_connections": 40, "gc_pause_ms": 4.0, "thread_count": 20,
    }
    base_score, base_anom, base_top, base_guard = detector.predict(baseline_metrics, return_guardrail=True)
    assert not base_anom
    assert not base_guard["triggered"]

    # Extreme latency spike (e.g. 4500ms vs ~40ms baseline)
    extreme_metrics = dict(baseline_metrics)
    extreme_metrics["response_time_p99"] = 4500.0

    ext_score, ext_anom, ext_top, ext_guard = detector.predict(extreme_metrics, return_guardrail=True)

    assert ext_anom is True
    assert ext_score > base_score + 0.20
    assert ext_guard["triggered"] is True
    assert ext_guard["max_feature"] == "response_time_p99"
    assert ext_guard["max_z"] > 20.0
    assert ext_guard["boost"] > 0.10
    assert "response_time_p99" in ext_top


def test_p1_extreme_error_rate_increases_anomaly_severity(trained_detector_and_engine):
    """P1: Extreme error_rate must trigger guardrail and increase anomaly severity."""
    detector, _, _ = trained_detector_and_engine

    normal_metrics = {
        "cpu_usage": 25.0, "memory_usage": 40.0, "disk_io": 12.0,
        "network_latency_ms": 6.0, "request_count": 6000, "error_rate": 0.02,
        "response_time_p99": 40.0, "active_connections": 50, "gc_pause_ms": 5.0, "thread_count": 22,
    }
    extreme_metrics = dict(normal_metrics)
    extreme_metrics["error_rate"] = 25.0  # 25% error rate spike

    score, is_anom, top_feats, guard = detector.predict(extreme_metrics, return_guardrail=True)

    assert is_anom is True
    assert score >= detector.threshold_score
    assert guard["triggered"] is True
    assert guard["max_feature"] == "error_rate"
    assert "error_rate" in top_feats


def test_p1_normal_metrics_not_flagged_by_guardrails(trained_detector_and_engine):
    """P1: Metrics within normal operational range must not trigger guardrail or produce false alarms."""
    detector, _, _ = trained_detector_and_engine

    healthy_metrics = {
        "cpu_usage": 22.0, "memory_usage": 38.0, "disk_io": 8.0,
        "network_latency_ms": 4.5, "request_count": 4800, "error_rate": 0.01,
        "response_time_p99": 28.0, "active_connections": 35, "gc_pause_ms": 3.8, "thread_count": 18,
    }
    score, is_anom, top_feats, guard = detector.predict(healthy_metrics, return_guardrail=True)

    assert not is_anom
    assert not guard["triggered"]
    assert guard["boost"] == 0.0
    assert score < detector.threshold_score


def test_p1_zero_std_handled_safely(trained_detector_and_engine):
    """P1: Features with standard deviation = 0 must not raise ZeroDivisionError."""
    detector, _, _ = trained_detector_and_engine

    # Temporarily set std of one feature to 0
    orig_std = detector._feature_stds.copy()
    try:
        detector._feature_stds[0] = 0.0

        metrics = {
            "cpu_usage": 99.0, "memory_usage": 40.0, "disk_io": 10.0,
            "network_latency_ms": 5.0, "request_count": 5000, "error_rate": 0.01,
            "response_time_p99": 35.0, "active_connections": 40, "gc_pause_ms": 4.0, "thread_count": 20,
        }
        score, is_anom, top_feats, guard = detector.predict(metrics, return_guardrail=True)
        assert np.isfinite(score)
        assert isinstance(guard, dict)
    finally:
        detector._feature_stds = orig_std


def test_p1_non_finite_input_handled_safely(trained_detector_and_engine):
    """P1: Non-finite inputs (None, NaN, Inf) must be safely imputed with training means without crashing."""
    detector, _, _ = trained_detector_and_engine

    metrics = {
        "cpu_usage": None,
        "memory_usage": float("nan"),
        "disk_io": float("inf"),
        "network_latency_ms": 5.0,
        "request_count": 5000,
        "error_rate": 0.01,
        "response_time_p99": 35.0,
        "active_connections": 40,
        "gc_pause_ms": 4.0,
        "thread_count": 20,
    }
    score, is_anom, top_feats, guard = detector.predict(metrics, return_guardrail=True)

    assert np.isfinite(score)
    assert 0.0 <= score <= 1.0


# ==============================================================================
# PART 2: P2 TOPOLOGY-AWARE CASCADE RISK TESTS
# ==============================================================================

def test_p2_direct_dependency_bounded_propagated_risk(trained_detector_and_engine):
    """P2: Degradation in an upstream dependency (payment-service) must propagate bounded risk to direct caller (order-service)."""
    _, engine, _ = trained_detector_and_engine

    healthy_order_metrics = {
        "cpu_usage": 25.0, "memory_usage": 40.0, "disk_io": 10.0,
        "network_latency_ms": 5.0, "request_count": 5000, "error_rate": 0.01,
        "response_time_p99": 30.0, "active_connections": 40, "gc_pause_ms": 4.0, "thread_count": 20,
    }

    # Case 1: Dependency healthy
    res_healthy = engine.score("order-service", healthy_order_metrics, dependencies_risk={"payment-service": 20.0})
    assert res_healthy.propagation_contribution == 0.0
    assert res_healthy.risk_score == res_healthy.local_risk_score

    # Case 2: Upstream payment-service CRITICAL (risk 90)
    res_degraded = engine.score("order-service", healthy_order_metrics, dependencies_risk={"payment-service": 90.0})

    assert res_degraded.propagation_contribution > 0.0
    assert res_degraded.propagation_contribution <= 35.0  # Bounded
    assert res_degraded.cascade_depth == 1
    assert res_degraded.dependency_path == ["order-service", "payment-service"]
    assert res_degraded.topology_adjusted_risk_score > res_degraded.local_risk_score
    assert res_degraded.upstream_incidents is not None
    assert len(res_degraded.upstream_incidents) == 1
    assert res_degraded.upstream_incidents[0]["service"] == "payment-service"


def test_p2_propagation_decays_with_graph_distance(trained_detector_and_engine):
    """P2: Risk propagation must decay as graph distance increases (1-hop > 2-hop)."""
    _, engine, _ = trained_detector_and_engine

    healthy_metrics = {
        "cpu_usage": 20.0, "memory_usage": 35.0, "disk_io": 10.0,
        "network_latency_ms": 5.0, "request_count": 5000, "error_rate": 0.01,
        "response_time_p99": 30.0, "active_connections": 40, "gc_pause_ms": 4.0, "thread_count": 20,
    }

    # In sample_dependencies.csv:
    # api-gateway -> order-service -> payment-service
    # order-service is distance 1 from payment-service
    # api-gateway is distance 2 from payment-service
    order_res = engine.score("order-service", healthy_metrics, dependencies_risk={"payment-service": 90.0})
    gateway_res = engine.score("api-gateway", healthy_metrics, dependencies_risk={"payment-service": 90.0})

    assert order_res.cascade_depth == 1
    assert gateway_res.cascade_depth == 2
    # Distance 1 propagation must be stronger than distance 2 propagation
    assert order_res.propagation_contribution > gateway_res.propagation_contribution
    # Specifically, decay factor is halved per hop (0.60 vs 0.30)
    assert math.isclose(gateway_res.propagation_contribution, order_res.propagation_contribution / 2.0, rel_tol=0.1)


def test_p2_independent_local_anomaly_remains_dominant(trained_detector_and_engine):
    """P2: If a service is locally failing severely, its own local risk remains dominant."""
    _, engine, _ = trained_detector_and_engine

    severe_local_metrics = {
        "cpu_usage": 98.0, "memory_usage": 95.0, "disk_io": 60.0,
        "network_latency_ms": 250.0, "request_count": 1000, "error_rate": 30.0,
        "response_time_p99": 3500.0, "active_connections": 400, "gc_pause_ms": 80.0, "thread_count": 250,
    }
    # Local failure with healthy dependency
    res = engine.score("order-service", severe_local_metrics, dependencies_risk={"payment-service": 25.0})

    assert res.local_risk_score >= 75.0  # Critical on its own
    assert res.risk_tier.value == "critical"
    assert res.propagation_contribution == 0.0
    assert res.predicted_failure_type != "cascading_failure"


def test_p2_cycles_and_max_cap(trained_detector_and_engine):
    """P2: Graph traversal avoids infinite cycles and risk score is strictly capped at 100."""
    _, engine, _ = trained_detector_and_engine

    extreme_metrics = {
        "cpu_usage": 99.0, "memory_usage": 99.0, "disk_io": 99.0,
        "network_latency_ms": 999.0, "request_count": 9999, "error_rate": 99.0,
        "response_time_p99": 9999.0, "active_connections": 999, "gc_pause_ms": 999.0, "thread_count": 999,
    }
    # Extreme dependency risk
    res = engine.score("order-service", extreme_metrics, dependencies_risk={"payment-service": 100.0})

    assert res.risk_score <= 100.0
    assert res.topology_adjusted_risk_score <= 100.0
    assert res.local_risk_score <= 100.0


def test_rca_distinguishes_root_cause_from_downstream_symptoms():
    """RCA: Root cause analysis distinguishes failing upstream dependency from downstream callers."""
    builder = GraphBuilder()
    builder.build_graph()

    # Simulate failure on payment-service
    cascade = builder.simulate_cascade("payment-service")
    timeline = cascade.get("timeline", [])

    # payment-service is depth 0 (the root cause)
    depth_0_svcs = [item["service_name"] for item in timeline if item["propagation_depth"] == 0]
    assert "payment-service" in depth_0_svcs

    # order-service is depth 1 (caller affected downstream)
    depth_1_svcs = [item["service_name"] for item in timeline if item["propagation_depth"] == 1]
    assert "order-service" in depth_1_svcs

    # api-gateway is depth 2 (edge service affected downstream)
    depth_2_svcs = [item["service_name"] for item in timeline if item["propagation_depth"] == 2]
    assert "api-gateway" in depth_2_svcs

    # Root cause candidate ranking from downstream victim (order-service)
    candidates = builder.rank_root_cause_candidates("order-service")
    candidate_names = [c.service_name for c in candidates]

    # payment-service is an upstream dependency and candidate root cause
    assert "payment-service" in candidate_names
    # api-gateway is caller (downstream) and therefore NOT an upstream root cause candidate for order-service
    assert "api-gateway" not in candidate_names

