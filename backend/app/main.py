"""
Synapse RiskOps - Core Backend
==============================
Owner: Person 2 | Week: 5
Framework: FastAPI (Python 3.11)

Core business logic service responsible for:
- PostgreSQL persistence (incidents, timeline, services)
- JWT Authentication & authorization
- Real-time Server-Sent Events (SSE) streaming to React frontend
- Microservice orchestration with ml-engine (8000) & genai-agent (8001)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.auth import router as auth_router
from app.api.incidents import router as incidents_router
from app.api.services import router as services_router
from app.api.risk_assessments import router as risk_assessments_router
from app.api.pipeline import router as pipeline_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Core backend API for Synapse RiskOps. Manages PostgreSQL incident records, "
        "JWT authentication, service topology, risk assessments, orchestration pipeline, "
        "and real-time SSE event dispatching to the dashboard."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Register API Routers
app.include_router(auth_router)
app.include_router(incidents_router)
app.include_router(services_router)
app.include_router(risk_assessments_router)
app.include_router(pipeline_router)

# =====================================================
# CORS Middleware
# =====================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================
# System & Health Endpoints
# =====================================================
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint used by Docker, load balancers, and frontend."""
    return {
        "status": "healthy",
        "service": "backend",
        "framework": "FastAPI",
        "version": settings.APP_VERSION,
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "framework": "FastAPI (Python 3.11)",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "health": "GET /health",
            "auth_login": "POST /api/auth/login",
            "auth_me": "GET /api/auth/me",
            "incidents": "GET /api/incidents",
            "incident_history": "GET /api/incidents/{id}/history",
            "stream": "GET /api/incidents/stream",
            "stream_status": "GET /api/incidents/stream/status",
            "alert": "POST /api/incidents/alert",
            "services": "GET /api/services",
            "services_topology": "GET /api/services/topology",
            "risk_assessments": "GET /api/risk-assessments",
            "risk_assessments_latest": "GET /api/risk-assessments/latest",
            "pipeline_diagnose": "POST /api/pipeline/diagnose-and-route",
            "pipeline_remediate": "POST /api/pipeline/remediate",
        },
    }
