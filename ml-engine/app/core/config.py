from pathlib import Path
from pydantic_settings import BaseSettings

"""
ml-engine/app/core/config.py
Owner: Person 2 | Week: 1-2

Central configuration for the ML Engine — env var loading (pydantic-settings),
CORS origins, DB connection string for sample-data/metrics storage, model
artifact paths (/app/models, mounted via ml_model_data volume in docker-compose.yml).

Imported by main.py and services modules instead of scattering configuration
values throughout the project.
"""


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