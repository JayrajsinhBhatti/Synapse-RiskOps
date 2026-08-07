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

        df = self.loader.load_metrics()

        # Remove duplicate rows
        df = df.drop_duplicates()

        # Remove rows with missing values
        df = df.dropna()

        # Convert timestamp column if present
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Numerical columns to normalize
        numeric_columns = []

        for column in ["cpu", "memory", "disk", "latency"]:
            if column in df.columns:
                numeric_columns.append(column)

        # Normalize numeric columns
        if numeric_columns:
            df[numeric_columns] = self.scaler.fit_transform(df[numeric_columns])

        return df


if __name__ == "__main__":

    processor = DataPreprocessor()

    cleaned_data = processor.preprocess_metrics()

    print("\nCleaned Dataset\n")

    print(cleaned_data.head())

    print("\nRows:", cleaned_data.shape[0])

    print("Columns:", cleaned_data.shape[1])