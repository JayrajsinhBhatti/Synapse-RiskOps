"""
Synapse RiskOps - Week 4 End-to-End Tests
==========================================

Owner: Person 2 | Week: 4

Validates:

    Metrics
      ↓
    ML prediction
      ↓
    Dependency graph
      ↓
    RCA context
      ↓
    Routing decision
      ↓
    Runbook / Escalation
"""

import sys
from pathlib import Path
from types import SimpleNamespace

# Ensure ml-engine root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schemas.prediction import FailureType
from app.services.week4_pipeline import Week4Pipeline


class FakeRiskEngine:
    """
    Lightweight fake ML engine for deterministic E2E testing.

    The real RiskEngine is already tested separately.
    This test focuses on Week 4 orchestration.
    """

    def score(self, service_name, metrics):

        return SimpleNamespace(
            service_name=service_name,
            risk_score=88.5,
            confidence=0.92,
            risk_tier="critical",
            predicted_failure_type=FailureType.CPU_SATURATION,
        )


def test_full_week4_auto_remediation_flow():

    pipeline = Week4Pipeline()

    engine = FakeRiskEngine()

    # =================================================
    # 1. METRICS → ML → GRAPH
    # =================================================

    analysis = pipeline.analyze_service(
        service="order-service",
        metrics={
            "cpu_usage": 96,
            "memory_usage": 91,
            "disk_io": 72,
            "network_latency_ms": 240,
            "request_count": 300,
            "error_rate": 17,
            "response_time_p99": 1100,
            "active_connections": 340,
            "gc_pause_ms": 75,
            "thread_count": 230,
        },
        risk_engine=engine,
    )

    prediction = analysis["prediction"]

    context = analysis["diagnosis_context"]

    # ML prediction
    assert prediction.risk_score == 88.5
    assert prediction.confidence == 0.92

    # Graph diagnosis
    assert context["service"] == "order-service"
    assert "root_cause_candidates_ranked" in context

    # =================================================
    # 2. SIMULATE PERSON 1 ROUTER RESULT
    # =================================================

    routing_decision = "auto_remediate"

    routing_confidence = 0.92

    # =================================================
    # 3. ROUTING → RUNBOOK
    # =================================================

    execution = pipeline.execute_decision(
        service="order-service",
        failure_type=FailureType.CPU_SATURATION,
        routing_decision=routing_decision,
        routing_confidence=routing_confidence,
    )

    # =================================================
    # 4. VERIFY REMEDIATION
    # =================================================

    assert execution.executed is True

    assert execution.status == "SUCCESS"

    assert execution.runbook_id == "RB-CPU-001"

    assert len(execution.actions_executed) > 0


def test_full_week4_escalation_flow():

    pipeline = Week4Pipeline()

    engine = FakeRiskEngine()

    # =================================================
    # ML → GRAPH
    # =================================================

    analysis = pipeline.analyze_service(
        service="order-service",
        metrics={
            "cpu_usage": 70,
            "memory_usage": 70,
            "disk_io": 30,
            "network_latency_ms": 100,
            "request_count": 5000,
            "error_rate": 4,
            "response_time_p99": 300,
            "active_connections": 100,
            "gc_pause_ms": 20,
            "thread_count": 80,
        },
        risk_engine=engine,
    )

    assert analysis["prediction"] is not None

    # =================================================
    # PERSON 1 ROUTER RESULT
    # =================================================

    routing_decision = "escalate"

    routing_confidence = 0.62

    # =================================================
    # ESCALATION → NO RUNBOOK
    # =================================================

    execution = pipeline.execute_decision(
        service="order-service",
        failure_type=FailureType.CPU_SATURATION,
        routing_decision=routing_decision,
        routing_confidence=routing_confidence,
    )

    assert execution.executed is False

    assert execution.status == "NOT_EXECUTED"

    assert len(execution.actions_executed) == 0


if __name__ == "__main__":
    print("Running test_full_week4_auto_remediation_flow...")
    test_full_week4_auto_remediation_flow()
    print("test_full_week4_auto_remediation_flow PASSED")
    print("Running test_full_week4_escalation_flow...")
    test_full_week4_escalation_flow()
    print("test_full_week4_escalation_flow PASSED")
    print("All tests passed!")
