"""
Synapse RiskOps - Dry-Run Twin API Router
=========================================
Endpoints for counterfactual predictive remediation simulations, multi-action
comparisons, uncertainty transparency, and authorized remediation execution.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, get_current_user_or_system
from app.core.database import get_db
from app.models.user import User
from app.schemas.dry_run import (
    DryRunExecuteRequest,
    DryRunExecuteResponse,
    DryRunSimulateRequest,
    DryRunSimulationResponse,
)
from app.services.dry_run_twin import dry_run_twin_service

router = APIRouter(
    prefix="/api/dry-run",
    tags=["Dry-Run Twin (Counterfactual Remediation)"],
)


@router.post(
    "/simulate",
    response_model=DryRunSimulationResponse,
    summary="Simulate counterfactual remediation actions without mutating live systems",
)
async def simulate_counterfactual_remediation(
    request: DryRunSimulateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_system),
):
    """
    Evaluates alternative remediation actions for a target service or incident:
    1. Computes predicted recovery time, health score, risk delta, residual error rate,
       p99 latency, and resource usage.
    2. Simulates downstream cascade blast radius using NetworkX topology graph.
    3. Evaluates Autonomy Budget qualification (auto-executable vs human approval).
    4. Ranks candidate actions side-by-side and recommends the safest option.
    5. Preserves strict safe separation: NEVER executes commands or alters running containers.
    """
    try:
        response = await dry_run_twin_service.simulate_remediation_options(
            service_name=request.service_name,
            incident_id=request.incident_id,
            candidate_actions=request.candidate_actions,
            environment=request.environment,
            current_metrics=request.current_metrics,
            db=db,
            user=current_user,
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dry-run simulation failed: {str(e)}",
        )


@router.get(
    "/history",
    summary="List past dry-run simulation audit records",
)
async def get_simulation_history(
    service_name: Optional[str] = Query(None, description="Filter by service name"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_system),
):
    """Retrieves immutable audit history of predictive simulations for auditability and replay."""
    try:
        return await dry_run_twin_service.get_simulation_history(
            service_name=service_name,
            limit=limit,
            db=db,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch simulation history: {str(e)}",
        )


@router.get(
    "/{simulation_id}",
    response_model=DryRunSimulationResponse,
    summary="Retrieve full details of a specific simulation record",
)
async def get_simulation_detail(
    simulation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_system),
):
    """Fetches complete inputs, candidate comparisons, and assumptions for a simulation ID."""
    sim = await dry_run_twin_service.get_simulation(simulation_id=simulation_id, db=db)
    if not sim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation {simulation_id} not found.",
        )
    return sim


@router.post(
    "/{simulation_id}/execute",
    response_model=DryRunExecuteResponse,
    summary="Separated authorized execution of a simulated remediation action",
)
async def execute_simulated_action(
    simulation_id: UUID,
    request: DryRunExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_system),
):
    """
    Explicit, authorized bridge from counterfactual simulation to production execution:
    1. Verifies operator permissions.
    2. Validates simulation record and autonomy budget policy.
    3. Dispatches Ansible Semaphore playbook to execute real remediation.
    """
    try:
        res = await dry_run_twin_service.execute_authorized_action(
            simulation_id=simulation_id,
            selected_action=request.selected_action,
            approval_notes=request.approval_notes,
            user=current_user,
            db=db,
        )
        return res
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
    except PermissionError as perm_err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(perm_err),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Execution dispatch failed: {str(e)}",
        )
