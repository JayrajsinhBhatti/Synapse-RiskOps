from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # =========================
    # Application Settings
    # =========================
    APP_NAME: str = "Synapse RiskOps ML Engine"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # =========================
    # Project Paths
    # =========================
    BASE_DIR: Path = Path(__file__).resolve().parents[3]
    DATA_DIR: Path = BASE_DIR / "sample-data"
    MODEL_DIR: Path = BASE_DIR / "models"

    # =========================
    # Dataset Files
    # =========================
    METRICS_FILE: Path = DATA_DIR / "sample_metrics.csv"
    LOGS_FILE: Path = DATA_DIR / "sample_logs.csv"
    DEPENDENCIES_FILE: Path = DATA_DIR / "sample_dependencies.csv"

    class Config:
        env_file = ".env"


settings = Settings()