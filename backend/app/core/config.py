"""
Synapse RiskOps - Core Backend Configuration
============================================
Owner: Person 2 | Week: 5

Centralized configuration settings loaded from environment variables.
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and environment variables."""

    # Server Settings
    APP_NAME: str = "Synapse RiskOps - Core Backend"
    APP_VERSION: str = "0.5.0"
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8080
    DEBUG: bool = False

    # PostgreSQL Database Connection
    # Default to localhost:5432 for host development; Docker Compose injects postgres:5432
    DATABASE_URL: str = (
        "postgresql+asyncpg://synapse_admin:synapse_dev_2026@127.0.0.1:5432/synapse_riskops"
    )
    DATABASE_URL_SYNC: str = (
        "postgresql://synapse_admin:synapse_dev_2026@127.0.0.1:5432/synapse_riskops"
    )

    # JWT Authentication
    JWT_SECRET: str = (
        "dev_only_jwt_secret_key_do_not_use_in_production_change_this_immediately_64chars"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440  # 24 hours

    # Inter-Service Communication URLs
    ML_ENGINE_URL: str = "http://ml-engine:8000"
    GENAI_AGENT_URL: str = "http://genai-agent:8001"

    # CORS Origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
