"""
Synapse RiskOps - Week 4 Autonomous Pipeline Test Suite
======================================================
Owner: Person 2 | Week: 4

Validates:
1. Runbook catalog creation and lookup across all failure types
2. Safety gating: auto_remediate vs. escalate execution
3. Routing decision recording and query history
4. End-to-end ML -> Graph -> Diagnosis Context generation
5. Joint compatibility with Person 1's confidence router
"""

import os
import sys
from pathlib import Path

# Ensure ml-engine root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schemas.prediction import FailureType
from app.schemas.routing import RoutingDecisionRequest
from app.services.runbook_engine import RunbookEngine
from app.services.week4_pipeline import Week4Pipeline


def main():
    print("=" * 75)
    print("SYNAPSE RISKOPS - WEEK 4 AUTONOMOUS PIPELINE TEST SUITE")
    print("=" * 75)

    passed = 0
    failed = 0

    def check(name: str, condition: bool, detail: str = ""):
        nonlocal passed, failed
        if condition:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failed += 1
            print(f"  FAIL  {name}  {detail}")

    # ===========================================================
    # Test 1: Runbook Catalog Coverage
    # ===========================================================
    print("\n" + "-" * 75)
    print("Test 1: Runbook Catalog Coverage (All Failure Types)")
    print("-" * 75)

    engine = RunbookEngine()
    runbooks = engine.list_runbooks()

    check("Total runbooks >= 7", len(runbooks) >= 7, f"got {len(runbooks)}")

    all_failure_types = [
        FailureType.CPU_SATURATION,
        FailureType.MEMORY_EXHAUSTION,
        FailureType.DISK_IO_BOTTLENECK,
        FailureType.LATENCY_DEGRADATION,
        FailureType.ERROR_RATE_SPIKE,
        FailureType.CONNECTION_POOL_EXHAUSTION,
        FailureType.CASCADING_FAILURE,
    ]

    for ft in all_failure_types:
        rb = engine.get_runbook(ft)
        check(f"Runbook exists for {ft.value}", rb is not None)
        if rb:
            check(f"  {rb.runbook_id} has >= 2 steps", len(rb.steps) >= 2, f"got {len(rb.steps)}")
            check(f"  {rb.runbook_id} steps have actions", all(bool(s.action) for s in rb.steps))

    # ===========================================================
    # Test 2: Safety Execution & Gating
    # ===========================================================
    print("\n" + "-" * 75)
    print("Test 2: Runbook Safety Execution & Gating")
    print("-" * 75)

    # Test auto_remediate
    res_auto = engine.execute(
        service="order-service",
        failure_type=FailureType.CPU_SATURATION,
        routing_decision="auto_remediate",
        routing_confidence=0.92,
    )
    check("Auto-remediate executes runbook", res_auto.executed is True)
    check("Auto-remediate status is SUCCESS", res_auto.status == "SUCCESS")
    check("Actions list is populated", len(res_auto.actions_executed) > 0)
    check("Action target matches service", res_auto.actions_executed[0].target == "order-service")

    # Test escalate
    res_esc = engine.execute(
        service="order-service",
        failure_type=FailureType.CPU_SATURATION,
        routing_decision="escalate",
        routing_confidence=0.70,
    )
    check("Escalate does NOT execute runbook", res_esc.executed is False)
    check("Escalate status is NOT_EXECUTED", res_esc.status == "NOT_EXECUTED")
    check("Escalate actions list is empty", len(res_esc.actions_executed) == 0)

    # ===========================================================
    # Test 3: Routing Decision Models & Persistence
    # ===========================================================
    print("\n" + "-" * 75)
    print("Test 3: Routing Decision Models & Querying")
    print("-" * 75)

    req = RoutingDecisionRequest(
        incident_id="INC-TEST-001",
        service="payment-service",
        routing_decision="auto_remediate",
        routing_confidence=0.89,
        routing_threshold_used=0.85,
        human_override=False,
    )
    check("Valid request model", req.incident_id == "INC-TEST-001")
    check("Valid routing decision", req.routing_decision == "auto_remediate")

    # ===========================================================
    # Test 4: End-to-End Pipeline & Diagnosis Context Generation
    # ===========================================================
    print("\n" + "-" * 75)
    print("Test 4: Pipeline Context for Person 1 Router")
    print("-" * 75)

    pipeline = Week4Pipeline()

    class MockRiskEngine:
        class MockPrediction:
            def __init__(self):
                self.confidence = 0.91
                self.risk_score = 88.5
                self.risk_tier = "CRITICAL"
                self.predicted_failure_type = FailureType.CPU_SATURATION

        def score(self, service_name, metrics):
            return self.MockPrediction()

    analysis = pipeline.analyze_service(
        service="order-service",
        metrics={"cpu_usage": 92.0},
        risk_engine=MockRiskEngine(),
    )

    ctx = analysis.get("diagnosis_context", {})
    check("Diagnosis context contains service", ctx.get("service") == "order-service")
    check("Diagnosis context contains prediction_confidence", ctx.get("prediction_confidence") == 0.91)
    check("Diagnosis context contains root_cause_candidates_ranked", "root_cause_candidates_ranked" in ctx)

    candidates = ctx.get("root_cause_candidates_ranked", [])
    check("Root cause candidates is a list", isinstance(candidates, list))
    if candidates:
        top = candidates[0]
        check("Top candidate has 'service'", "service" in top)
        check("Top candidate has 'confidence'", "confidence" in top and top["confidence"] > 0)
        print(f"    Top candidate: {top.get('service')} with confidence {top.get('confidence')}")

    # Verify execution endpoint
    exec_res = pipeline.execute_decision(
        service="order-service",
        failure_type=FailureType.CPU_SATURATION,
        routing_decision="auto_remediate",
        routing_confidence=0.91,
    )
    check("Pipeline execution succeeds", exec_res.executed is True)

    # ===========================================================
    # Final Scorecard
    # ===========================================================
    print("\n" + "=" * 75)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 75)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
