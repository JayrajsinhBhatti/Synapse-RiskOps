"""
Synapse RiskOps - Composite Risk Engine
=========================================
Owner: Person 2 | Week: 2

Combines the Isolation Forest anomaly score with the Statsmodels
failure forecast into a single composite risk score (0-100).

Formula:
    risk_score = (w_anomaly * anomaly_score + w_forecast * forecast_risk) * 100

Tiers (agreed in Week 2 contracts):
    < 40  -> HEALTHY
    40-75 -> WATCH
    >= 75 -> CRITICAL

Person 1's GenAI agent uses the CRITICAL tier to trigger root cause analysis.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone
from loguru import logger
from typing import Dict, Optional, Tuple, List, Any

from app.models.anomaly_detector import AnomalyDetector
from app.models.failure_forecaster import FailureForecaster
from app.services.graph_builder import GraphBuilder
from app.schemas.prediction import (
    PredictionResponse, AnomalyDetail, ForecastDetail, RiskTier,
)
import networkx as nx


class RiskEngine:
    """
    Orchestrates anomaly detection + failure forecasting into a unified
    risk assessment per service.
    """

    # Weighting for composite score
    ANOMALY_WEIGHT = 0.60
    FORECAST_WEIGHT = 0.40
    ACTIVE_ANOMALY_WEIGHT = 0.85
    ACTIVE_FORECAST_WEIGHT = 0.15

    # Risk tier thresholds
    HEALTHY_THRESHOLD = 40.0
    WATCH_THRESHOLD = 75.0

    def __init__(self):
        self.anomaly_detector = AnomalyDetector(contamination=0.03)
        self.failure_forecaster = FailureForecaster(forecast_periods=12)
        self.graph_builder = GraphBuilder()
        try:
            self.graph_builder.build_graph()
        except Exception as e:
            logger.warning(f"Could not build dependency graph in RiskEngine: {e}")
        self._service_risk_cache: Dict[str, Dict[str, Any]] = {}
        self.is_trained = False
        self._last_trained_at: Optional[str] = None
        self._training_samples: int = 0
        self._services_list = []

    def train(self, df: pd.DataFrame) -> Dict:
        """
        Train both sub-models on historical metrics data.

        Args:
            df: Full metrics DataFrame from CSVLoader/DataPreprocessor.
                Must have raw (non-scaled) values for forecaster.

        Returns:
            Combined training summary.
        """
        logger.info(f"Training RiskEngine on {len(df)} samples...")

        # Train anomaly detector (it handles its own scaling)
        anomaly_summary = self.anomaly_detector.train(df)

        # Train failure forecaster (needs raw timestamps + values)
        forecast_summary = self.failure_forecaster.train(df)

        self.is_trained = True
        self._last_trained_at = datetime.now(timezone.utc).isoformat()
        self._training_samples = len(df)
        self._services_list = list(df["service_name"].unique())

        combined = {
            "anomaly_detector": anomaly_summary,
            "failure_forecaster": forecast_summary,
            "total_samples": len(df),
            "services": self._services_list,
            "trained_at": self._last_trained_at,
        }

        logger.info(f"RiskEngine training complete: {len(self._services_list)} services")
        return combined

    def score(
        self,
        service_name: str,
        metrics: Dict,
        dependencies_risk: Optional[Dict[str, float]] = None,
    ) -> PredictionResponse:
        """
        Compute the composite risk score for a service with P2 topology-aware cascade propagation.

        Args:
            service_name: Name of the microservice.
            metrics: Dict of metric values (raw, not scaled).
            dependencies_risk: Optional explicit mapping of dependency name -> risk score.

        Returns:
            PredictionResponse with full risk assessment and cascade details.
        """
        if not self.is_trained:
            raise RuntimeError("RiskEngine not trained. Call train() first.")

        # 1. Anomaly Detection (P1: returns guardrail_info)
        anomaly_score, is_anomaly, top_features, guardrail_info = self.anomaly_detector.predict(
            metrics, return_guardrail=True
        )

        # 2. Failure Forecast
        forecast_result = self.failure_forecaster.forecast(service_name)
        forecast_risk = forecast_result["forecast_risk"]

        # 3. Composite Local Risk Score (P0-3: 85% anomaly + 15% forecast during active anomaly; 60/40 normal)
        if is_anomaly:
            raw_score = (
                self.ACTIVE_ANOMALY_WEIGHT * anomaly_score
                + self.ACTIVE_FORECAST_WEIGHT * forecast_risk
            )
        else:
            raw_score = (
                self.ANOMALY_WEIGHT * anomaly_score
                + self.FORECAST_WEIGHT * forecast_risk
            )
        local_risk_score = round(min(100.0, max(0.0, raw_score * 100)), 2)

        # Update cache for this service
        self._service_risk_cache[service_name] = {
            "local_risk_score": local_risk_score,
            "is_anomaly": is_anomaly,
            "anomaly_score": anomaly_score,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # 4. Topology-Aware Cascade Risk Propagation (P2)
        upstream_incidents, propagation_contribution, best_path, best_depth = self._calculate_cascade_risk(
            service_name, dependencies_risk
        )

        topology_adjusted_risk_score = round(
            min(100.0, max(local_risk_score, local_risk_score + propagation_contribution)), 2
        )

        # Final risk score is topology-adjusted, but local score is preserved
        final_risk_score = topology_adjusted_risk_score
        risk_tier = self._classify_tier(final_risk_score)

        # 5. Compute confidence (higher when both models agree)
        confidence = self._compute_confidence(anomaly_score, forecast_risk)

        # 6. Determine predicted failure type (P0-2: prioritize live top features during anomaly)
        if is_anomaly:
            predicted_failure_type = self._infer_failure_type(top_features)
            if predicted_failure_type == "none":
                predicted_failure_type = forecast_result["predicted_failure_type"]
        elif propagation_contribution >= 15.0:
            predicted_failure_type = "cascading_failure"
        else:
            predicted_failure_type = forecast_result["predicted_failure_type"]

        # 7. Compute 95% confidence interval based on model confidence
        uncertainty_margin = round((1.0 - confidence) * 15.0, 2)
        ci_lower = round(max(0.0, final_risk_score - uncertainty_margin), 2)
        ci_upper = round(min(100.0, final_risk_score + uncertainty_margin), 2)
        risk_ci = {"lower": ci_lower, "upper": ci_upper}

        forecast_ci = {
            "lower": round(max(0.0, forecast_risk - (1.0 - confidence) * 0.15), 4),
            "upper": round(min(100.0, forecast_risk + (1.0 - confidence) * 0.15), 4),
        }

        # Build response
        return PredictionResponse(
            predicted_at=datetime.now(timezone.utc).isoformat(),
            model_name="synapse_riskops_v1",
            service_name=service_name,
            risk_score=final_risk_score,
            risk_threshold=self.WATCH_THRESHOLD,
            risk_tier=risk_tier,
            confidence=round(confidence, 4),
            confidence_interval=risk_ci,
            predicted_failure_type=predicted_failure_type,
            prediction_horizon_minutes=forecast_result["prediction_horizon_minutes"],
            anomaly_detail=AnomalyDetail(
                anomaly_score=round(anomaly_score, 4),
                is_anomaly=is_anomaly,
                top_contributing_features=top_features,
                guardrail_info=guardrail_info,
            ),
            forecast_detail=ForecastDetail(
                forecast_risk=round(forecast_risk, 4),
                predicted_failure_type=forecast_result["predicted_failure_type"],
                prediction_horizon_minutes=forecast_result["prediction_horizon_minutes"],
                trend_direction=forecast_result["trend_direction"],
                confidence_interval=forecast_ci,
            ),
            local_risk_score=local_risk_score,
            topology_adjusted_risk_score=topology_adjusted_risk_score,
            upstream_incidents=upstream_incidents if upstream_incidents else None,
            propagation_contribution=round(propagation_contribution, 2) if propagation_contribution > 0 else 0.0,
            dependency_path=best_path,
            cascade_depth=best_depth,
        )

    def _calculate_cascade_risk(
        self,
        service_name: str,
        dependencies_risk: Optional[Dict[str, float]] = None,
    ) -> Tuple[List[Dict[str, Any]], float, Optional[List[str]], Optional[int]]:
        """
        P2 Topology-Aware Cascade Risk Calculation.
        Finds upstream dependencies (services called by this service).
        Applies distance decay: factor = 0.60 * (0.50 ** (distance - 1)).
        Cycles are safely avoided by using NetworkX shortest paths.
        """
        if not self.graph_builder.is_built or service_name not in self.graph_builder.graph:
            return [], 0.0, None, None

        graph = self.graph_builder.graph
        upstream_nodes = list(nx.descendants(graph, service_name))
        if not upstream_nodes:
            return [], 0.0, None, None

        upstream_incidents = []
        contributions = []
        best_path = None
        best_depth = None
        max_contrib = 0.0

        for dep in upstream_nodes:
            # Check dependency risk score
            dep_risk: Optional[float] = None
            if dependencies_risk and dep in dependencies_risk:
                dep_risk = float(dependencies_risk[dep])
            elif dep in self._service_risk_cache:
                dep_risk = float(self._service_risk_cache[dep].get("local_risk_score", 0.0))

            if dep_risk is None or dep_risk < self.HEALTHY_THRESHOLD:
                continue

            try:
                path = nx.shortest_path(graph, service_name, dep)
            except nx.NetworkXNoPath:
                continue

            dist = len(path) - 1
            if dist < 1:
                continue

            # Decay factor: d=1 -> 0.60, d=2 -> 0.30, d=3 -> 0.15
            decay = 0.60 * (0.50 ** (dist - 1))

            # Criticality weighting along path
            is_crit_path = True
            for u, v in zip(path[:-1], path[1:]):
                if not graph[u][v].get("is_critical", False):
                    is_crit_path = False
                    break
            crit_mult = 1.0 if is_crit_path else 0.70

            # Bounded raw contribution from upstream degradation above healthy baseline (30)
            raw_contrib = max(0.0, (dep_risk - 30.0)) * decay * crit_mult
            contrib = min(35.0, raw_contrib)

            upstream_incidents.append({
                "service": dep,
                "risk_score": round(dep_risk, 2),
                "distance": dist,
                "path": path,
                "contribution": round(contrib, 2),
            })
            contributions.append(contrib)

            if contrib > max_contrib:
                max_contrib = contrib
                best_path = path
                best_depth = dist

        if not contributions:
            return [], 0.0, None, None

        # Cumulative propagation: dominant contributor + dampened remainder, capped at 35.0
        sorted_contribs = sorted(contributions, reverse=True)
        total_propagation = sorted_contribs[0]
        for c in sorted_contribs[1:]:
            total_propagation += c * 0.25
        total_propagation = min(35.0, total_propagation)

        return upstream_incidents, total_propagation, best_path, best_depth

    def _classify_tier(self, risk_score: float) -> RiskTier:
        """Classify the risk score into a tier."""
        if risk_score >= self.WATCH_THRESHOLD:
            return RiskTier.CRITICAL
        elif risk_score >= self.HEALTHY_THRESHOLD:
            return RiskTier.WATCH
        return RiskTier.HEALTHY

    def _compute_confidence(self, anomaly_score: float, forecast_risk: float) -> float:
        """
        Compute model confidence.
        Higher when both models agree (both high or both low).
        Lower when models disagree.
        """
        # Agreement: both models rate it similarly
        agreement = 1.0 - abs(anomaly_score - forecast_risk)

        # Base confidence from model certainty (extremes = more confident)
        anomaly_certainty = abs(anomaly_score - 0.5) * 2  # 0 at 0.5, 1 at extremes
        forecast_certainty = abs(forecast_risk - 0.5) * 2

        confidence = (
            0.4 * agreement
            + 0.35 * anomaly_certainty
            + 0.25 * forecast_certainty
        )

        return min(1.0, max(0.0, confidence))

    def _infer_failure_type(self, top_features: list) -> str:
        """Infer failure type from anomalous features."""
        feature_to_failure = {
            "cpu_usage": "cpu_saturation",
            "memory_usage": "memory_exhaustion",
            "error_rate": "error_rate_spike",
            "network_latency_ms": "latency_degradation",
            "response_time_p99": "latency_degradation",
            "active_connections": "connection_pool_exhaustion",
            "disk_io": "disk_io_bottleneck",
            "gc_pause_ms": "memory_exhaustion",
            "thread_count": "connection_pool_exhaustion",
        }
        if top_features:
            return feature_to_failure.get(top_features[0], "none")
        return "none"

    def get_status(self) -> Dict:
        """Return current model status for /api/model/status."""
        return {
            "anomaly_detector_trained": self.anomaly_detector.is_trained,
            "failure_forecaster_trained": self.failure_forecaster.is_trained,
            "training_samples": self._training_samples,
            "services_modeled": self._services_list,
            "last_trained_at": self._last_trained_at,
        }


if __name__ == "__main__":
    from app.services.csv_loader import CSVLoader

    loader = CSVLoader()
    df = loader.load_metrics()

    engine = RiskEngine()
    summary = engine.train(df)

    print("\n--- Training Summary ---")
    print(f"  Samples: {summary['total_samples']}")
    print(f"  Services: {summary['services']}")

    # Score a healthy service
    healthy_metrics = {
        "cpu_usage": 25.0, "memory_usage": 45.0, "disk_io": 10.0,
        "network_latency_ms": 5.0, "request_count": 8000, "error_rate": 0.02,
        "response_time_p99": 15.0, "active_connections": 50,
        "gc_pause_ms": 4.0, "thread_count": 20,
    }

    result = engine.score("auth-service", healthy_metrics)
    print(f"\n--- Healthy Service Score ---")
    print(f"  Risk Score: {result.risk_score}")
    print(f"  Risk Tier: {result.risk_tier}")
    print(f"  Confidence: {result.confidence}")

    # Score an anomalous service
    critical_metrics = {
        "cpu_usage": 95.0, "memory_usage": 93.0, "disk_io": 70.0,
        "network_latency_ms": 250.0, "request_count": 200, "error_rate": 18.0,
        "response_time_p99": 1200.0, "active_connections": 350,
        "gc_pause_ms": 80.0, "thread_count": 250,
    }

    result = engine.score("postgres-primary", critical_metrics)
    print(f"\n--- Critical Service Score ---")
    print(f"  Risk Score: {result.risk_score}")
    print(f"  Risk Tier: {result.risk_tier}")
    print(f"  Confidence: {result.confidence}")
    print(f"  Failure Type: {result.predicted_failure_type}")
    print(f"  Horizon: {result.prediction_horizon_minutes} min")
    print(f"  Anomaly Score: {result.anomaly_detail.anomaly_score}")
    print(f"  Top Features: {result.anomaly_detail.top_contributing_features}")
