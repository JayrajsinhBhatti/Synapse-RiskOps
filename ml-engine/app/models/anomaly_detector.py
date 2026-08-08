import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler

from app.services.preprocessing import DataPreprocessor


class AnomalyDetector:
    """
    Detects unusual server behavior using Isolation Forest.

    The final anomaly score is normalized between 0 and 1:
        0 -> less anomalous
        1 -> more anomalous
    """

    def __init__(self):
        self.preprocessor = DataPreprocessor()

        self.model = IsolationForest(
            n_estimators=100,
            contamination=0.05,
            random_state=42
        )

        self.score_scaler = MinMaxScaler()

        self.feature_columns = [
            "cpu_usage",
            "memory_usage",
            "disk_io",
            "network_latency_ms",
            "request_count",
            "error_rate",
            "response_time_p99",
            "active_connections",
            "gc_pause_ms",
            "thread_count"
        ]

        self.is_trained = False

    def _prepare_features(self, df: pd.DataFrame):
        """
        Select the numerical features required by the ML model.
        """

        missing_columns = [
            column
            for column in self.feature_columns
            if column not in df.columns
        ]

        if missing_columns:
            raise ValueError(
                f"Missing required feature columns: {missing_columns}"
            )

        return df[self.feature_columns]

    def train(self):
        """
        Train the Isolation Forest model using preprocessed metrics.
        """

        df = self.preprocessor.preprocess_metrics()

        X = self._prepare_features(df)

        self.model.fit(X)

        self.is_trained = True

        return self.model

    def predict(self, df: pd.DataFrame = None):
        """
        Detect anomalies and generate normalized anomaly scores.
        """

        if not self.is_trained:
            self.train()

        if df is None:
            df = self.preprocessor.preprocess_metrics()

        X = self._prepare_features(df)

        # Isolation Forest prediction:
        # 1  = normal
        # -1 = anomaly
        predictions = self.model.predict(X)

        # Lower decision_function values are more anomalous.
        raw_scores = self.model.decision_function(X)

        # Convert the direction so higher = more anomalous.
        anomaly_values = -raw_scores

        # Normalize anomaly scores to 0-1.
        normalized_scores = self.score_scaler.fit_transform(
            anomaly_values.reshape(-1, 1)
        ).flatten()

        result = df.copy()

        result["anomaly"] = predictions

        result["anomaly_score"] = normalized_scores

        result["status"] = result["anomaly_score"].apply(
            self._get_status
        )

        return result

    @staticmethod
    def _get_status(score: float):
        """
        Convert anomaly score into a simple status.
        """

        if score >= 0.80:
            return "CRITICAL"

        if score >= 0.50:
            return "WARNING"

        return "NORMAL"


if __name__ == "__main__":

    detector = AnomalyDetector()

    print("Training Isolation Forest...")

    detector.train()

    print("Model trained successfully.")

    print("\nRunning anomaly detection...")

    results = detector.predict()

    print("\nAnomaly Detection Results:")
    print(
        results[
            [
                "timestamp",
                "service_name",
                "cpu_usage",
                "memory_usage",
                "response_time_p99",
                "anomaly_score",
                "status"
            ]
        ].head(20).to_string(index=False)
    )

    print("\nStatus Summary:")
    print(results["status"].value_counts())

    print("\nAnomaly Score Range:")
    print("Minimum:", results["anomaly_score"].min())
    print("Maximum:", results["anomaly_score"].max())