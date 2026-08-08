"""
Synapse RiskOps - FastAPI ML Engine
====================================
Owner: Person 2 | Week: 1-2

Main entry point for the ML Engine service.
- Registers all API routers (risk scoring, data ingestion, graph traversal)
- Configures CORS middleware
- Trains ML models on startup using sample data
- Exposes health check for Docker orchestration
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from typing import Optional

from app.core.config import settings
from app.services.risk_engine import RiskEngine
from app.services.csv_loader import CSVLoader
from app.api import risk_score, ingest


# =====================================================
# Global Risk Engine Instance
# =====================================================
_risk_engine: Optional[RiskEngine] = None


def get_risk_engine() -> Optional[RiskEngine]:
    """Accessor for the global RiskEngine instance."""
    return _risk_engine


# =====================================================
# Application Lifespan (Startup / Shutdown)
# =====================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    On startup: load sample data and train ML models.
    On shutdown: cleanup resources.
    """
    global _risk_engine

    logger.info("=" * 60)
    logger.info(f"Starting {settings.APP_NAME}")
    logger.info("=" * 60)

    # Initialize and train the risk engine
    _risk_engine = RiskEngine()

    try:
        loader = CSVLoader()
        df = loader.load_metrics()

        logger.info(f"Loaded {len(df)} metric rows for training")

        summary = _risk_engine.train(df)
        logger.info(
            f"Models trained: {summary['anomaly_detector']['samples']} samples, "
            f"{len(summary['services'])} services"
        )
    except FileNotFoundError as e:
        logger.warning(f"No training data found: {e}. Models will need manual training via /api/ingest/metrics.")
    except Exception as e:
        logger.error(f"Model training failed on startup: {e}. Service will start but scoring will be unavailable.")

    yield  # Application runs here

    # Shutdown cleanup
    logger.info("Shutting down ML Engine")
    _risk_engine = None


# =====================================================
# Application Factory
# =====================================================
app = FastAPI(
    title="Synapse RiskOps - ML Engine",
    description=(
        "Anomaly detection (Isolation Forest), failure prediction (Statsmodels), "
        "composite risk scoring, and dependency graph APIs for the "
        "Synapse RiskOps autonomous risk operations pipeline."
    ),
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# =====================================================
# CORS Middleware
# =====================================================
cors_origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================
# Register API Routers
# =====================================================
app.include_router(risk_score.router)
app.include_router(ingest.router)


# =====================================================
# System Endpoints
# =====================================================
@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint used by Docker and load balancers.
    Returns 200 OK if the service is running.
    """
    engine = get_risk_engine()
    models_ready = engine is not None and engine.is_trained

    return {
        "status": "healthy",
        "service": "ml-engine",
        "version": "0.2.0",
        "models_ready": models_ready,
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Synapse RiskOps - ML Engine",
        "version": "0.2.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "risk_score": "POST /api/risk-score",
            "batch_score": "POST /api/risk-score/batch",
            "ingest_metrics": "POST /api/ingest/metrics",
            "ingest_logs": "POST /api/ingest/logs",
            "model_status": "GET /api/model/status",
        },
    }
