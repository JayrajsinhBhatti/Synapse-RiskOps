"""
Synapse RiskOps - Anomaly Detector (Isolation Forest)
======================================================
Owner: Person 2 | Week: 2

Unsupervised anomaly detection using scikit-learn's Isolation Forest.
Trains on historical server metrics and produces anomaly scores (0-1)
for incoming service metric snapshots.

Key design decisions:
- contamination=0.03 (expect ~3% anomalies in training data)
- Scores are normalized to [0, 1] where 1 = most anomalous
- Feature importance is approximated via single-feature ablation
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from loguru import logger
from typing import Dict, List, Tuple, Optional


class AnomalyDetector:
    """
    Isolation Forest wrapper for real-time anomaly detection
    on server infrastructure metrics.
    """

    # Feature columns expected by the model
    FEATURE_COLUMNS = [
        "cpu_usage", "memory_usage", "disk_io", "network_latency_ms",
        "request_count", "error_rate", "response_time_p99",
        "active_connections", "gc_pause_ms", "thread_count",
    ]

    def __init__(self, contamination: float = 0.03, random_state: int = 42):
        """
        Args:
            contamination: Expected proportion of anomalies in training data.
            random_state: Seed for reproducibility.
        """
        self.contamination = contamination
        self.random_state = random_state

        self.model = IsolationForest(
            n_estimators=200,
            contamination=contamination,
            max_samples="auto",
            random_state=random_state,
            n_jobs=-1,
        )

        self.scaler = StandardScaler()
        self.is_trained = False
        self._feature_means: Optional[np.ndarray] = None
        self._feature_stds: Optional[np.ndarray] = None

    def train(self, df: pd.DataFrame) -> Dict:
        """
        Train the Isolation Forest on historical metrics.

        Args:
            df: DataFrame with columns matching FEATURE_COLUMNS.

        Returns:
            Training summary dict with stats.
        """
        # Extract and validate feature columns
        available_features = [c for c in self.FEATURE_COLUMNS if c in df.columns]
        if len(available_features) < 3:
            raise ValueError(
                f"Need at least 3 feature columns. Found: {available_features}"
            )

        X = df[available_features].copy()

        # Handle any remaining NaN values
        X = X.fillna(X.median())

        # Store raw statistics before scaling
        self._feature_means = X.mean().values
        self._feature_stds = X.std().values

        # Fit scaler and transform
        X_scaled = self.scaler.fit_transform(X)

        # Train Isolation Forest
        self.model.fit(X_scaled)
        self.is_trained = True
        self._trained_features = available_features

        # Compute training anomaly scores for threshold calibration
        train_scores = self._raw_scores(X_scaled)

        logger.info(
            f"AnomalyDetector trained on {len(X)} samples, "
            f"{len(available_features)} features. "
            f"Mean anomaly score: {train_scores.mean():.4f}"
        )

        return {
            "samples": len(X),
            "features": available_features,
            "mean_score": float(train_scores.mean()),
            "std_score": float(train_scores.std()),
            "threshold_score": float(np.percentile(train_scores, 97)),
        }

    def predict(self, metrics: Dict) -> Tuple[float, bool, List[str]]:
        """
        Score a single service metrics snapshot.

        Args:
            metrics: Dict with keys matching FEATURE_COLUMNS.

        Returns:
            Tuple of (anomaly_score, is_anomaly, top_contributing_features).
            anomaly_score is in [0, 1] where 1 = most anomalous.
        """
        if not self.is_trained:
            raise RuntimeError("AnomalyDetector has not been trained. Call train() first.")

        # Build feature vector
        feature_values = []
        for col in self._trained_features:
            val = metrics.get(col, 0.0)
            feature_values.append(float(val))

        X = pd.DataFrame([feature_values], columns=self._trained_features)
        X_scaled = self.scaler.transform(X)

        # Get anomaly score (normalized to 0-1)
        score = self._raw_scores(X_scaled)[0]

        # Determine if anomaly
        is_anomaly = score > 0.55  # Calibrated threshold

        # Find top contributing features via deviation from mean
        contributions = self._feature_contributions(feature_values)
        top_features = sorted(contributions.items(), key=lambda x: x[1], reverse=True)[:3]
        top_feature_names = [f[0] for f in top_features]

        return score, is_anomaly, top_feature_names

    def predict_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Score a batch of metrics rows. Adds 'anomaly_score' and
        'is_anomaly_predicted' columns to the returned DataFrame.
        """
        if not self.is_trained:
            raise RuntimeError("AnomalyDetector has not been trained. Call train() first.")

        X = df[self._trained_features].fillna(0)
        X_scaled = self.scaler.transform(X)
        scores = self._raw_scores(X_scaled)

        result = df.copy()
        result["anomaly_score"] = scores
        result["is_anomaly_predicted"] = (scores > 0.55).astype(int)

        return result

    def _raw_scores(self, X_scaled: np.ndarray) -> np.ndarray:
        """
        Convert Isolation Forest's decision_function output to [0, 1] range.
        IsolationForest.decision_function returns negative scores for anomalies,
        positive for normal points. We invert and normalize.
        """
        raw = self.model.decision_function(X_scaled)
        # Invert: more negative = more anomalous -> higher score
        # Normalize using sigmoid-like transform
        scores = 1.0 / (1.0 + np.exp(5 * raw))
        return np.clip(scores, 0.0, 1.0)

    def _feature_contributions(self, feature_values: List[float]) -> Dict[str, float]:
        """
        Approximate feature importance by computing z-score deviation
        from training distribution for each feature.
        """
        contributions = {}
        for i, col in enumerate(self._trained_features):
            if self._feature_stds[i] > 0:
                z = abs(feature_values[i] - self._feature_means[i]) / self._feature_stds[i]
            else:
                z = 0.0
            contributions[col] = float(z)
        return contributions


if __name__ == "__main__":
    from app.services.csv_loader import CSVLoader

    loader = CSVLoader()
    df = loader.load_metrics()

    detector = AnomalyDetector()
    summary = detector.train(df)
    print("\n--- Training Summary ---")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    # Test single prediction with an anomalous-looking input
    test_metrics = {
        "cpu_usage": 95.0,
        "memory_usage": 92.0,
        "disk_io": 50.0,
        "network_latency_ms": 200.0,
        "request_count": 500,
        "error_rate": 15.0,
        "response_time_p99": 800.0,
        "active_connections": 300,
        "gc_pause_ms": 50.0,
        "thread_count": 200,
    }

    score, is_anom, top_feats = detector.predict(test_metrics)
    print(f"\n--- Single Prediction ---")
    print(f"  Score: {score:.4f}")
    print(f"  Is Anomaly: {is_anom}")
    print(f"  Top Features: {top_feats}")

    # Test batch prediction
    results = detector.predict_batch(df.head(20))
    print(f"\n--- Batch Prediction (first 20 rows) ---")
    print(results[["service_name", "anomaly_score", "is_anomaly_predicted"]].to_string())