"""
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
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from loguru import logger
from typing import Dict, List, Tuple, Optional, Any


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
        self.threshold_score: float = 0.50

    def train(self, df: pd.DataFrame) -> Dict:
        """
        Train the Isolation Forest on historical metrics.
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
        self.threshold_score = float(np.percentile(train_scores, 100 * (1.0 - self.contamination)))

        logger.info(
            f"AnomalyDetector trained on {len(X)} samples, "
            f"{len(available_features)} features. "
            f"Mean anomaly score: {train_scores.mean():.4f}, "
            f"Calibrated threshold: {self.threshold_score:.4f}"
        )

        return {
            "samples": len(X),
            "features": available_features,
            "mean_score": float(train_scores.mean()),
            "std_score": float(train_scores.std()),
            "threshold_score": self.threshold_score,
        }

    def predict(self, metrics: Dict, return_guardrail: bool = False):
        """
        Score a single service metrics snapshot.
        Applies P1-A dynamic rescaling and P1-B univariate guardrails.
        """
        if not self.is_trained:
            raise RuntimeError("AnomalyDetector has not been trained. Call train() first.")

        # Build feature vector safely handling non-finite or missing values
        feature_values = []
        for i, col in enumerate(self._trained_features):
            val = metrics.get(col, None)
            try:
                if val is not None and np.isfinite(float(val)):
                    val_float = float(val)
                else:
                    val_float = float(self._feature_means[i])
            except (ValueError, TypeError):
                val_float = float(self._feature_means[i])
            feature_values.append(val_float)

        X = pd.DataFrame([feature_values], columns=self._trained_features)
        X_scaled = self.scaler.transform(X)

        # Get base anomaly score via P1-A rescaled transformation
        base_score = float(self._raw_scores(X_scaled)[0])

        # Apply P1-B univariate guardrail
        score, guardrail_info = self._compute_guardrails(feature_values, base_score)
        self.last_guardrail_info = guardrail_info

        # Determine if anomaly
        is_anomaly = bool(score >= self.threshold_score or guardrail_info.get("triggered", False))

        # Find top contributing features
        contributions = self._feature_contributions(feature_values)
        top_features = sorted(
            contributions.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        top_feature_names = [f[0] for f in top_features]

        if return_guardrail:
            return score, is_anomaly, top_feature_names, guardrail_info
        return score, is_anomaly, top_feature_names

    def predict_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Score a batch of metrics rows.
        """
        if not self.is_trained:
            raise RuntimeError("AnomalyDetector has not been trained. Call train() first.")

        # Impute missing with means
        X = df[self._trained_features].copy()
        for i, col in enumerate(self._trained_features):
            X[col] = pd.to_numeric(X[col], errors="coerce").fillna(self._feature_means[i])

        X_scaled = self.scaler.transform(X)
        base_scores = self._raw_scores(X_scaled)

        adjusted_scores = []
        for i, (_, row) in enumerate(df.iterrows()):
            vals = []
            for j, col in enumerate(self._trained_features):
                val = row.get(col, None)
                try:
                    vals.append(float(val) if val is not None and np.isfinite(float(val)) else self._feature_means[j])
                except (ValueError, TypeError):
                    vals.append(self._feature_means[j])
            adj_s, _ = self._compute_guardrails(vals, float(base_scores[i]))
            adjusted_scores.append(adj_s)

        scores = np.array(adjusted_scores)
        result = df.copy()
        result["anomaly_score"] = scores
        result["is_anomaly_predicted"] = (scores >= self.threshold_score).astype(int)
        return result

    def evaluate(self, df: pd.DataFrame) -> Dict:
        """
        Evaluate predictions using ground-truth is_anomaly labels.
        """
        if "is_anomaly" not in df.columns:
            raise ValueError("DataFrame must contain 'is_anomaly' column.")

        results = self.predict_batch(df)

        y_true = df["is_anomaly"].astype(int)
        y_pred = results["is_anomaly_predicted"].astype(int)

        return {
            "accuracy": accuracy_score(y_true, y_pred),
            "precision": precision_score(y_true, y_pred, zero_division=0),
            "recall": recall_score(y_true, y_pred, zero_division=0),
            "f1_score": f1_score(y_true, y_pred, zero_division=0),
        }

    def _raw_scores(self, X_scaled: np.ndarray) -> np.ndarray:
        """
        Convert Isolation Forest's decision_function output to [0, 1] range.
        P1-A Dynamic anomaly-score rescaling:
        Preserves model ordering and continuity at r=0 (boundary between normal and anomaly).
        For r >= 0 (normal): 1.0 / (1.0 + np.exp(8.0 * r)), bounded in (0, 0.50]
        For r < 0 (anomalous): 0.50 + 0.50 * (1.0 - np.exp(-15.0 * np.abs(raw))), expanding [0.50, 1.0)
        """
        raw = self.model.decision_function(X_scaled)

        scores = np.empty_like(raw, dtype=float)
        normal_mask = raw >= 0.0
        scores[normal_mask] = 1.0 / (1.0 + np.exp(8.0 * raw[normal_mask]))
        scores[~normal_mask] = 0.50 + 0.50 * (1.0 - np.exp(-15.0 * np.abs(raw[~normal_mask])))

        return np.clip(scores, 0.0, 1.0)

    def _compute_guardrails(self, feature_values: List[float], base_score: float) -> Tuple[float, Dict[str, Any]]:
        """
        P1-B Hybrid univariate z-score guardrail:
        Detects extreme deviations in individual metrics (e.g. 10x latency spike) that
        might be diluted in multi-dimensional space.
        Threshold z > 4.0 (beyond 99.99% of normal distribution).
        Boost is bounded by (1.0 - base_score) * 0.40 * severity so score never exceeds 1.0.
        """
        if self._feature_means is None or self._feature_stds is None:
            return base_score, {"triggered": False, "max_z": 0.0, "boost": 0.0}

        z_scores: Dict[str, float] = {}
        max_z = 0.0
        max_feat = ""

        for i, col in enumerate(self._trained_features):
            val = feature_values[i]
            if not np.isfinite(val):
                continue

            mean_val = self._feature_means[i]
            std_val = self._feature_stds[i]

            if std_val > 0.0:
                z = float(abs(val - mean_val) / std_val)
            else:
                z = 0.0

            z_scores[col] = z
            if z > max_z:
                max_z = z
                max_feat = col

        if max_z > 4.0:
            severity = min(1.0, (max_z - 4.0) / 16.0)
            boost = (1.0 - base_score) * 0.40 * severity
            final_score = min(1.0, base_score + boost)
            guardrail_info = {
                "triggered": True,
                "max_z": round(max_z, 2),
                "max_feature": max_feat,
                "boost": round(boost, 4),
                "feature_z_scores": {k: round(v, 2) for k, v in z_scores.items() if v > 2.0},
            }
            return final_score, guardrail_info

        return base_score, {
            "triggered": False,
            "max_z": round(max_z, 2),
            "max_feature": max_feat,
            "boost": 0.0,
            "feature_z_scores": {k: round(v, 2) for k, v in z_scores.items() if v > 2.0},
        }

    def _feature_contributions(self, feature_values: List[float]) -> Dict[str, float]:
        """
        Approximate feature importance using z-score deviation
        from training distribution.
        """
        contributions = {}
        for i, col in enumerate(self._trained_features):
            val = feature_values[i]
            if not np.isfinite(val):
                contributions[col] = 0.0
                continue
            if self._feature_stds[i] > 0:
                z = abs(val - self._feature_means[i]) / self._feature_stds[i]
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

    print("\n--- Single Prediction ---")
    print(f"  Score: {score:.4f}")
    print(f"  Is Anomaly: {is_anom}")
    print(f"  Top Features: {top_feats}")

    # Test batch prediction
    results = detector.predict_batch(df.head(20))

    print("\n--- Batch Prediction (first 20 rows) ---")
    print(
        results[
            ["service_name", "anomaly_score", "is_anomaly_predicted"]
        ].to_string()
    )

    # Evaluate against ground-truth labels
    evaluation = detector.evaluate(df)

    print("\n--- Evaluation ---")
    print(f"  Accuracy:  {evaluation['accuracy']:.4f}")
    print(f"  Precision: {evaluation['precision']:.4f}")
    print(f"  Recall:    {evaluation['recall']:.4f}")
    print(f"  F1 Score:  {evaluation['f1_score']:.4f}")