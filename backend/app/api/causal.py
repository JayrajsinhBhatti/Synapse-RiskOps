"""
Synapse RiskOps - Chaos-Calibrated Causal Graph API
===================================================
Provides endpoints for:
1. Running controlled chaos experiments with safety bounds and automated restoration
2. Fetching the calibrated NetworkX causal graph with provenance tiers
3. Inspecting the statistical evidence and DiD distributions supporting any edge
4. Seeding baseline calibrations for immediate exploration
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.auth import get_current_user_or_system
from app.core.database import get_db
from app.models.causal import CausalExperimentRecord
from app.models.user import User
from app.schemas.causal import (
    CausalEdgeEvidenceResponse,
    CausalExperimentRequest,
    CausalExperimentResult,
    CausalGraphResponse,
)
from app.services.causal_calibrator import causal_calibrator

logger = logging.getLogger("synapse.api.causal")

router = APIRouter(
    prefix="/api/causal",
    tags=["Chaos-Calibrated Causal Graph"],
)


@router.post(
    "/experiments/run",
    response_model=CausalExperimentResult,
    summary="Run a controlled chaos experiment to calibrate graph dependencies",
)
async def run_causal_experiment(
    req: CausalExperimentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_system),
):
    """
    Executes a bounded, controlled fault injection experiment on the target service:
    1. Records pre-injection baseline telemetry for target, neighbors, and control service.
    2. Injects bounded fault (latency, error storm, unavailability) into isolated test/demo environment.
    3. Measures downstream propagation effects and elapsed delay tau.
    4. Automatically restores the injected fault (guaranteed rollback).
    5. Computes Difference-in-Differences (DiD) effect size and updates edge calibration.
    """
    operator_name = getattr(current_user, "username", "Admin SRE")
    try:
        result = await causal_calibrator.run_controlled_experiment(
            request=req,
            operator=operator_name,
            db=db,
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.exception("Error executing controlled chaos experiment")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Experiment execution failed: {str(e)}",
        )


@router.get(
    "/graph",
    response_model=CausalGraphResponse,
    summary="Get the NetworkX dependency graph calibrated with experimental causal evidence",
)
async def get_calibrated_causal_graph(
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the complete service graph with experimentally calibrated edges:
    - Preserves all declared dependencies
    - Annotates edges with causal strength [0.0 - 1.0] and propagation delay tau (ms)
    - Distinguishes provenance tiers: VALIDATED_CAUSAL, OBSERVED, DECLARED, UNCERTAIN
    - Provides summary KPIs (validated count, mean delay, confidence)
    """
    try:
        payload = await causal_calibrator.get_causal_graph_payload(db=db)
        return payload
    except Exception as e:
        logger.exception("Failed to retrieve calibrated causal graph")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate causal graph: {str(e)}",
        )


@router.get(
    "/edges/{source}/{target}/evidence",
    summary="Inspect supporting controlled experiments and statistical evidence for an edge",
)
async def get_edge_evidence(
    source: str,
    target: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns deep-dive evidence for a directed causal edge:
    - DiD effect size distribution
    - Observed propagation delay
    - Repeatability and confidence scores
    - Historical supporting experiment records
    """
    try:
        evidence = await causal_calibrator.get_edge_evidence(source=source, target=target, db=db)
        return evidence
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        logger.exception(f"Failed to inspect edge evidence for {source} -> {target}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to inspect evidence: {str(e)}",
        )


@router.post(
    "/seed-baselines",
    summary="Seed default verified baseline calibrations for demonstration",
)
async def seed_baseline_calibrations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_system),
):
    """Seeds verified initial causal calibrations for the core microservices."""
    seeded = await causal_calibrator.seed_verified_baselines(db=db)
    return {
        "status": "success",
        "seeded_calibrations": seeded,
        "message": f"Successfully seeded {seeded} verified causal calibrations.",
    }


@router.get(
    "/experiments/history",
    summary="List audit records of recent controlled chaos experiments",
)
async def get_experiment_history(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Lists audit logs of past chaos calibration experiments."""
    try:
        q = select(CausalExperimentRecord).order_by(CausalExperimentRecord.started_at.desc()).limit(limit)
        res = await db.execute(q)
        records = res.scalars().all()
        return [
            {
                "experiment_id": r.experiment_id,
                "target_service": r.target_service,
                "control_service": r.control_service,
                "fault_type": r.fault_type,
                "intensity": r.intensity,
                "duration_seconds": r.duration_seconds,
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "injected_by": r.injected_by,
                "observed_impact_count": len(r.observed_impacts) if isinstance(r.observed_impacts, list) else 0,
            }
            for r in records
        ]
    except Exception as e:
        logger.debug(f"History query error: {e}")
        return []
