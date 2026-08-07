"""
Synapse RiskOps - FastAPI ML Engine
====================================
Minimal entry point for Phase 1 (Project Setup).
Full implementation comes in Phase 2.

This file exists so Docker can build and health-check the service
even before we add ML logic.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# =====================================================
# Application Factory
# =====================================================
app = FastAPI(
    title="Synapse RiskOps - ML Engine",
    description="Anomaly detection, failure prediction, risk scoring, and dependency graph APIs",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =====================================================
# CORS Middleware
# =====================================================
cors_origins = os.getenv("ML_ENGINE_CORS_ORIGINS", "http://localhost:5173,http://localhost:8080")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================
# Health Check Endpoint
# =====================================================
@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint used by Docker and load balancers.
    Returns 200 OK if the service is running.
    """
    return {
        "status": "healthy",
        "service": "ml-engine",
        "version": "0.1.0",
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Synapse RiskOps - ML Engine",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
