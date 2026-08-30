"""
genai-agent/tests/test_pipeline_integration.py
Owner: Person 1 | Week: 3-4

End-to-end integration test for the complete LangGraph pipeline.

Stubs out:
  - ML Engine HTTP calls (requests.post / requests.get) via unittest.mock
  - Gemini LLM calls via monkeypatching the chain.invoke methods

Run from genai-agent/ directory:
  python -m pytest tests/test_pipeline_integration.py -v
"""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SAMPLE_METRICS = {
    "service_name": "order-service",
    "cpu_usage": 78.5,
    "memory_usage": 85.2,
    "disk_io": 32.1,
    "network_latency_ms": 45.3,
    "request_count": 5200,
    "error_rate": 8.5,
    "response_time_p99": 180.0,
    "active_connections": 120,
    "gc_pause_ms": 12.5,
    "thread_count": 48,
    "timestamp": "2026-08-30T21:58:00Z",
}

SAMPLE_LOGS = [
    {"service": "order-service",  "message": "DB connection timeout after 5s"},
    {"service": "payment-service","message": "Connection pool utilization 92%"},
    {"service": "order-service",  "message": "Request latency exceeded threshold"},
]

# Fake ML Engine risk-score response (high confidence → triggers auto_remediate path)
ML_RISK_SCORE_RESPONSE = {
    "risk_score": 0.91,
    "risk_tier": "critical",
    "confidence": 0.92,
    "predicted_failure_type": "db_connection_exhaustion",
    "prediction_horizon_minutes": 15,
}

# Fake ML Engine graph/traverse response
ML_GRAPH_RESPONSE = {
    "service": "order-service",
    "upstream_dependencies": ["payment-service", "inventory-service"],
    "downstream_dependents": [],
}

# Fake RCA output returned by the mocked Gemini chain
FAKE_RCA_OUTPUT = {
    "root_cause_candidates_ranked": [
        {
            "cause": "Database connection pool exhaustion in payment-service",
            "confidence": 0.88,
            "affected_services": ["payment-service", "order-service"],
            "reason": (
                "Connection pool utilization at 92% combined with DB timeouts "
                "indicates the pool is saturated."
            ),
        }
    ]
}

# Fake guidance output returned by the mocked Gemini structured-output chain
class FakeGuidance:
    guidance_steps = [
        "Immediately increase connection pool size for payment-service.",
        "Enable connection pool monitoring alerts.",
        "Review and close stale connections.",
    ]
    guidance_relevance_score = 91
    guidance_relevance_rubric_notes = (
        "Guidance is directly tied to the identified root cause and predicted failure."
    )


# ---------------------------------------------------------------------------
# Helper: build the mock for requests.post / requests.get
# ---------------------------------------------------------------------------

def _make_response(json_data: dict, status_code: int = 200) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


# ---------------------------------------------------------------------------
# Test 1: confidence_router in isolation
# ---------------------------------------------------------------------------

class TestConfidenceRouter:
    def test_auto_remediate_when_both_thresholds_met(self):
        from app.routing.confidence_router import confidence_router

        state = {
            "prediction_confidence": 0.92,
            "root_cause_candidates_ranked": [{"cause": "db exhaustion", "confidence": 0.88}],
        }
        result = confidence_router(state)
        assert result["routing_decision"] == "auto_remediate", (
            f"Expected auto_remediate, got: {result['routing_decision']}"
        )
        assert "routing_reason" in result
        print("\n[auto_remediate] routing_reason:", result["routing_reason"])

    def test_escalate_when_ml_confidence_low(self):
        from app.routing.confidence_router import confidence_router

        state = {
            "prediction_confidence": 0.70,  # below 0.85
            "root_cause_candidates_ranked": [{"cause": "db exhaustion", "confidence": 0.88}],
        }
        result = confidence_router(state)
        assert result["routing_decision"] == "escalate"
        print("\n[escalate-ml] routing_reason:", result["routing_reason"])

    def test_escalate_when_rca_confidence_low(self):
        from app.routing.confidence_router import confidence_router

        state = {
            "prediction_confidence": 0.92,
            "root_cause_candidates_ranked": [{"cause": "unknown", "confidence": 0.55}],
        }
        result = confidence_router(state)
        assert result["routing_decision"] == "escalate"
        print("\n[escalate-rca] routing_reason:", result["routing_reason"])

    def test_escalate_when_no_candidates(self):
        from app.routing.confidence_router import confidence_router

        state = {
            "prediction_confidence": 0.95,
            "root_cause_candidates_ranked": [],
        }
        result = confidence_router(state)
        assert result["routing_decision"] == "escalate"
        print("\n[escalate-empty] routing_reason:", result["routing_reason"])


# ---------------------------------------------------------------------------
# Test 2: Full pipeline.invoke() end-to-end
# ---------------------------------------------------------------------------

class TestPipelineEndToEnd:
    @patch("app.ml_node.requests.get")
    @patch("app.ml_node.requests.post")
    def test_pipeline_invoke_returns_all_keys(
        self,
        mock_post: MagicMock,
        mock_get: MagicMock,
    ):
        """
        Runs the full pipeline with mocked ML Engine HTTP responses and
        mocked Gemini LLM chains. Asserts all expected state keys are present.
        """
        # --- Stub ML Engine HTTP calls ---
        mock_post.return_value = _make_response(ML_RISK_SCORE_RESPONSE)
        mock_get.return_value = _make_response(ML_GRAPH_RESPONSE)

        # --- Stub Gemini chains ---
        import app.agents.root_cause_identifier as rca_module
        import app.agents.proactive_guidance_generator as guidance_module

        original_rca_chain = rca_module.chain
        original_guidance_chain = guidance_module.chain

        mock_rca_chain = MagicMock()
        mock_rca_chain.invoke.return_value = FAKE_RCA_OUTPUT

        mock_guidance_chain = MagicMock()
        mock_guidance_chain.invoke.return_value = FakeGuidance()

        rca_module.chain = mock_rca_chain
        guidance_module.chain = mock_guidance_chain

        try:
            from app.graph.state_graph import pipeline

            initial_state = {
                "metrics": SAMPLE_METRICS,
                "logs": SAMPLE_LOGS,
            }

            result = pipeline.invoke(initial_state)

            # ---------------------------------------------------------------
            # Assert all expected keys are present
            # ---------------------------------------------------------------
            assert "risk_score"                  in result, "Missing risk_score"
            assert "risk_tier"                   in result, "Missing risk_tier"
            assert "prediction_confidence"        in result, "Missing prediction_confidence"
            assert "predicted_failure_type"       in result, "Missing predicted_failure_type"
            assert "prediction_horizon_minutes"   in result, "Missing prediction_horizon_minutes"
            assert "dependency_graph"             in result, "Missing dependency_graph"
            assert "observations"                 in result, "Missing observations"
            assert "root_cause_candidates_ranked" in result, "Missing root_cause_candidates_ranked"
            assert "guidance"                     in result, "Missing guidance"
            assert "routing_decision"             in result, "Missing routing_decision"
            assert "routing_reason"               in result, "Missing routing_reason"

            # ---------------------------------------------------------------
            # Assert value types/shapes are correct
            # ---------------------------------------------------------------
            assert isinstance(result["risk_score"], float)
            assert result["risk_tier"] in ("low", "medium", "high", "critical")
            assert isinstance(result["root_cause_candidates_ranked"], list)
            assert len(result["root_cause_candidates_ranked"]) > 0
            assert result["routing_decision"] in ("auto_remediate", "escalate")

            # With confidence 0.92 (ML) and 0.88 (RCA) — both above threshold
            assert result["routing_decision"] == "auto_remediate", (
                f"Expected auto_remediate but got: {result['routing_decision']}\n"
                f"routing_reason: {result['routing_reason']}"
            )

            # ---------------------------------------------------------------
            # Pretty-print the full result for manual inspection
            # ---------------------------------------------------------------
            print("\n" + "=" * 60)
            print("PIPELINE RESULT")
            print("=" * 60)
            print(f"  risk_score:                {result['risk_score']}")
            print(f"  risk_tier:                 {result['risk_tier']}")
            print(f"  prediction_confidence:     {result['prediction_confidence']}")
            print(f"  predicted_failure_type:    {result['predicted_failure_type']}")
            print(f"  prediction_horizon_min:    {result['prediction_horizon_minutes']}")
            print(f"\n  observations:")
            for svc, msgs in result["observations"].items():
                print(f"    {svc}: {msgs}")
            print(f"\n  root_cause_candidates_ranked:")
            for c in result["root_cause_candidates_ranked"]:
                print(f"    [{c['confidence']:.2f}] {c['cause']}")
            guidance = result.get("guidance", {})
            if guidance:
                print(f"\n  guidance.summary:         {guidance.get('summary', '')[:80]}")
                print(f"  guidance.relevance_score: {guidance.get('relevance_score', 'N/A')}")
                print(f"  guidance.immediate_actions:")
                for action in guidance.get("immediate_actions", []):
                    print(f"    - {action}")
            print(f"\n  routing_decision:          {result['routing_decision']}")
            print(f"  routing_reason:            {result['routing_reason']}")
            print("=" * 60)

        finally:
            # Always restore the original chains
            rca_module.chain = original_rca_chain
            guidance_module.chain = original_guidance_chain
