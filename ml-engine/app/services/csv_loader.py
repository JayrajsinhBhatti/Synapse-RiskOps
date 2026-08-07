import pandas as pd
from pathlib import Path

from app.core.config import settings


class CSVLoader:
    """
    Service responsible for loading CSV datasets used by the ML Engine.
    """

    def __init__(self):
        self.metrics_file = settings.METRICS_FILE
        self.logs_file = settings.LOGS_FILE

    def load_metrics(self):
        """
        Load the server metrics dataset.
        """

        if not self.metrics_file.exists():
            raise FileNotFoundError(
                f"Metrics file not found: {self.metrics_file}"
            )

        df = pd.read_csv(self.metrics_file)

        return df

    def load_logs(self):
        """
        Load the server logs dataset.
        """

        if not self.logs_file.exists():
            raise FileNotFoundError(
                f"Logs file not found: {self.logs_file}"
            )

        df = pd.read_csv(self.logs_file)

        return df


if __name__ == "__main__":

    loader = CSVLoader()

    print("Loading Metrics Dataset...\n")

    metrics = loader.load_metrics()

    print(metrics.head())

    print("\nRows :", metrics.shape[0])
    print("Columns :", metrics.shape[1])

    print("\nLoading Logs Dataset...\n")

    logs = loader.load_logs()

    print(logs.head())

    print("\nRows :", logs.shape[0])
    print("Columns :", logs.shape[1])