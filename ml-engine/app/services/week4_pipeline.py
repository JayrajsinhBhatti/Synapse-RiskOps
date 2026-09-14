"""
Synapse RiskOps - Week 4 Autonomous Pipeline
=============================================

Owner: Person 2 | Week: 4

Real integration pipeline:

Metrics
    ↓
RiskEngine
    ↓
PredictionResponse
    ↓
Dependency Graph
    ↓
Diagnosis Context
    ↓
Person 1 Confidence Router
    ↓
Routing Decision
    ↓
Runbook Execution
"""

from typing import Any, Dict

from app.schemas.prediction import FailureType
from app.services.graph_builder import get_graph_builder
from app.services.runbook_engine import runbook_engine


class Week4Pipeline:
    """
    Orchestrates the Week 4 ML → Graph → Routing → Runbook flow.

    Person 1 owns the confidence-routing algorithm.

    Person 2 owns:
    - ML prediction integration
    - dependency graph integration
    - routing API
    - reusable runbooks
    - remediation execution
    """

    def __init__(self):
        self.graph_builder = get_graph_builder()

    # =====================================================
    # SAFE SERIALIZATION HELPER
    # =====================================================

    @staticmethod
    def _enum_value(value: Any) -> Any:
        """
        Safely convert Enum values to their underlying value.

        Works with both:
            Enum objects
            plain strings

        This prevents errors such as:
            AttributeError: 'str' object has no attribute 'value'
        """

        if hasattr(value, "value"):
            return value.value

        return value

    # =====================================================
    # ML + GRAPH ANALYSIS
    # =====================================================

    def analyze_service(
        self,
        service: str,
        metrics: Dict[str, float],
        risk_engine: Any,
    ) -> Dict[str, Any]:
        """
        Run the existing ML RiskEngine and dependency graph.

        Flow:

            metrics
                ↓
            RiskEngine.score()
                ↓
            PredictionResponse
                ↓
            GraphBuilder
                ↓
            RCA candidates
        """

        # -------------------------------------------------
        # 1. ML RISK PREDICTION
        # -------------------------------------------------

        prediction = risk_engine.score(
            service_name=service,
            metrics=metrics,
        )

        # -------------------------------------------------
        # 2. DEPENDENCY GRAPH / RCA
        # -------------------------------------------------

        candidates = self.graph_builder.rank_root_cause_candidates(
            service
        )

        ranked_candidates = []

        for candidate in candidates:
            # Estimate confidence based on graph distance and criticality
            base_conf = 0.92 if candidate.distance <= 1 else max(0.60, 0.90 - (candidate.distance - 1) * 0.10)
            if self._enum_value(candidate.criticality) in ("CRITICAL", "HIGH"):
                base_conf = min(0.98, base_conf + 0.04)

            ranked_candidates.append(
                {
                    "service": candidate.service_name,
                    "service_name": candidate.service_name,
                    "label": f"{self._enum_value(candidate.service_type).lower()}_issue",
                    "confidence": round(base_conf, 2),
                    "criticality": self._enum_value(
                        candidate.criticality
                    ),
                    "distance": candidate.distance,
                    "dependency_type": self._enum_value(
                        candidate.dependency_type
                    ),
                    "service_type": self._enum_value(
                        candidate.service_type
                    ),
                    "path": candidate.path,
                }
            )

        # -------------------------------------------------
        # 3. FAILURE TYPE
        # -------------------------------------------------

        failure_type = self._enum_value(
            prediction.predicted_failure_type
        )

        # -------------------------------------------------
        # 4. RISK TIER
        # -------------------------------------------------

        risk_tier = self._enum_value(
            prediction.risk_tier
        )

        # -------------------------------------------------
        # 5. BUILD PERSON 1 ROUTER CONTEXT
        # -------------------------------------------------

        diagnosis_context = {
            "service": service,

            "prediction_confidence": prediction.confidence,

            "risk_score": prediction.risk_score,

            "risk_tier": risk_tier,

            "predicted_failure_type": failure_type,

            "root_cause_candidates_ranked": ranked_candidates,
        }

        # -------------------------------------------------
        # 6. RETURN COMPLETE ANALYSIS
        # -------------------------------------------------

        return {
            "prediction": prediction,

            "diagnosis_context": diagnosis_context,
        }

    # =====================================================
    # ROUTING → RUNBOOK
    # =====================================================

    def execute_decision(
        self,
        service: str,
        failure_type: FailureType,
        routing_decision: str,
        routing_confidence: float,
    ):
        """
        Execute the routing decision.

        auto_remediate
            ↓
        Runbook Engine
            ↓
        Simulated remediation

        escalate
            ↓
        No remediation
        """

        return runbook_engine.execute(
            service=service,
            failure_type=failure_type,
            routing_decision=routing_decision,
            routing_confidence=routing_confidence,
        )


# =====================================================
# MODULE-LEVEL SINGLETON
# =====================================================

week4_pipeline = Week4Pipeline()