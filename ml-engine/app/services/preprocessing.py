import pandas as pd
from sklearn.preprocessing import StandardScaler

from app.services.csv_loader import CSVLoader


class DataPreprocessor:
    """
    Cleans and prepares datasets before ML models use them.
    """

    def __init__(self):
        self.loader = CSVLoader()
        self.scaler = StandardScaler()

    def preprocess_metrics(self):

        # Load metrics dataset
        df = self.loader.load_metrics()

        # Remove duplicate rows
        df = df.drop_duplicates()

        # Remove rows with missing values
        df = df.dropna()

        # Convert timestamp column to datetime
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Numeric columns used for ML
        numeric_columns = [
            "cpu_usage",
            "memory_usage",
            "disk_io",
            "network_latency_ms",
            "request_count",
            "error_rate",
            "response_time_p99",
            "active_connections",
            "gc_pause_ms",
            "thread_count",
        ]

        # Keep only columns that actually exist
        numeric_columns = [
            col for col in numeric_columns if col in df.columns
        ]

        # Keep target/metadata columns intact if present
        metadata_cols = ["timestamp", "service_name", "is_anomaly"]

        # Normalize numerical features
        if numeric_columns:
            df[numeric_columns] = self.scaler.fit_transform(
                df[numeric_columns]
            )

        return df

    def get_features_and_labels(self):
        """
        Helper method to extract X (features) and y (is_anomaly label).
        """
        df = self.preprocess_metrics()
        
        feature_cols = [
            "cpu_usage", "memory_usage", "disk_io", "network_latency_ms",
            "request_count", "error_rate", "response_time_p99",
            "active_connections", "gc_pause_ms", "thread_count"
        ]
        feature_cols = [col for col in feature_cols if col in df.columns]

        X = df[feature_cols]
        y = df["is_anomaly"] if "is_anomaly" in df.columns else None

        return X, y, df


if __name__ == "__main__":
    processor = DataPreprocessor()
    cleaned_data = processor.preprocess_metrics()

    print("\n--- Cleaned Dataset ---")
    print(cleaned_data.head())
    print("\nRows:", cleaned_data.shape[0])
    print("Columns:", cleaned_data.shape[1])
    
    if "is_anomaly" in cleaned_data.columns:
        print("\nAnomaly Distribution in Ground Truth:")
        print(cleaned_data["is_anomaly"].value_counts())