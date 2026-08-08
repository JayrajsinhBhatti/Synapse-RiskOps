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
from typing import Dict, Optional

from app.models.anomaly_detector import AnomalyDetector
from app.models.failure_forecaster import FailureForecaster
from app.schemas.prediction import (
    PredictionResponse, AnomalyDetail, ForecastDetail, RiskTier,
)


class RiskEngine:
    """
    Orchestrates anomaly detection + failure forecasting into a unified
    risk assessment per service.
    """

    # Weighting for composite score
    ANOMALY_WEIGHT = 0.60
    FORECAST_WEIGHT = 0.40

    # Risk tier thresholds
    HEALTHY_THRESHOLD = 40.0
    WATCH_THRESHOLD = 75.0

    def __init__(self):
        self.anomaly_detector = AnomalyDetector(contamination=0.03)
        self.failure_forecaster = FailureForecaster(forecast_periods=12)
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

    def score(self, service_name: str, metrics: Dict) -> PredictionResponse:
        """
        Compute the composite risk score for a service.

        Args:
            service_name: Name of the microservice.
            metrics: Dict of metric values (raw, not scaled).

        Returns:
            PredictionResponse with full risk assessment.
        """
        if not self.is_trained:
            raise RuntimeError("RiskEngine not trained. Call train() first.")

        # 1. Anomaly Detection
        anomaly_score, is_anomaly, top_features = self.anomaly_detector.predict(metrics)

        # 2. Failure Forecast
        forecast_result = self.failure_forecaster.forecast(service_name)
        forecast_risk = forecast_result["forecast_risk"]

        # 3. Composite Risk Score
        raw_score = (
            self.ANOMALY_WEIGHT * anomaly_score
            + self.FORECAST_WEIGHT * forecast_risk
        )
        risk_score = round(min(100.0, max(0.0, raw_score * 100)), 2)

        # 4. Classify tier
        risk_tier = self._classify_tier(risk_score)

        # 5. Compute confidence (higher when both models agree)
        confidence = self._compute_confidence(anomaly_score, forecast_risk)

        # 6. Determine predicted failure type
        predicted_failure_type = forecast_result["predicted_failure_type"]
        if predicted_failure_type == "none" and is_anomaly:
            # Anomaly detected but forecaster doesn't predict specific failure
            # Use the top contributing feature to infer failure type
            predicted_failure_type = self._infer_failure_type(top_features)

        # Build response
        return PredictionResponse(
            predicted_at=datetime.now(timezone.utc).isoformat(),
            model_name="synapse_riskops_v1",
            service_name=service_name,
            risk_score=risk_score,
            risk_threshold=self.WATCH_THRESHOLD,
            risk_tier=risk_tier,
            confidence=round(confidence, 4),
            predicted_failure_type=predicted_failure_type,
            prediction_horizon_minutes=forecast_result["prediction_horizon_minutes"],
            anomaly_detail=AnomalyDetail(
                anomaly_score=round(anomaly_score, 4),
                is_anomaly=is_anomaly,
                top_contributing_features=top_features,
            ),
            forecast_detail=ForecastDetail(
                forecast_risk=round(forecast_risk, 4),
                predicted_failure_type=forecast_result["predicted_failure_type"],
                prediction_horizon_minutes=forecast_result["prediction_horizon_minutes"],
                trend_direction=forecast_result["trend_direction"],
            ),
        )

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
