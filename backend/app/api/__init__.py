"""
Synapse RiskOps - Backend API Routers Package
=============================================
Owner: Person 2 | Week: 5
"""

from app.api.auth import router as auth_router
from app.api.incidents import router as incidents_router
from app.api.services import router as services_router
from app.api.risk_assessments import router as risk_assessments_router
from app.api.pipeline import router as pipeline_router

__all__ = [
    "auth_router",
    "incidents_router",
    "services_router",
    "risk_assessments_router",
    "pipeline_router",
]
