"""
ml-engine/app/core/config.py
Owner: Person 2 | Week: 1-2

Central configuration for the ML Engine — env var loading (pydantic-settings),
CORS origins, DB connection string for sample-data/metrics storage, model
artifact paths (/app/models, mounted via ml_model_data volume in docker-compose.yml).
Imported by main.py and services/ modules instead of scattering os.getenv() calls.
"""
