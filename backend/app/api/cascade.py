"""
Synapse RiskOps - Cascade Interception Planner API Router
=========================================================
Endpoints for simulating failure propagation, ranking protective interception plans,
and executing authorized cascade mitigations under Autonomy Budget governance.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user, get_current_user_or_system
from app.core.database import get_db
from app.models.user import User
from app.schemas.cascade import (
    CascadeExecutePlanRequest,
    CascadeExecutePlanResponse,
    CascadeSimulateRequest,
    CascadeSimulationResponse,
    InterceptionPlan,
)
from app.services.cascade_planner import cascade_planner_service

router = APIRouter(
    prefix="/api/cascade",
    tags=["Cascade Interception Planner"],
)


@router.post(
    "/simulate",
    response_model=CascadeSimulationResponse,
    summary="Simulate cascading failure and generate ranked interception plans",
)
async def simulate_cascade_propagation(
    request: CascadeSimulateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_system),
):
    """
    Simulates failure propagation from a seed service across the NetworkX graph.
    Generates and ranks competing protective interception plans, comparing
    before vs after blast-radius impact.
    """
    try:
        graph = await cascade_planner_service.build_topology_graph(db)
        simulation = cascade_planner_service.simulate_propagation(
            graph=graph,
            seed_service=request.seed_service,
            failure_type=request.failure_type,
            severity=request.severity,
        )

        plans = cascade_planner_service.generate_interception_plans(
            graph=graph,
            seed_service=request.seed_service,
            baseline_sim=simulation,
            db=db,
            user=current_user,
        )

        recommended = next((p for p in plans if p.is_recommended), plans[0] if plans else None)

        topology_summary = {
            "total_nodes": graph.number_of_nodes(),
            "total_edges": graph.number_of_edges(),
            "density": round(float(len(graph.edges)) / max(1, len(graph.nodes) * (len(graph.nodes) - 1)), 3),
            "seed_in_degree": graph.in_degree(request.seed_service) if request.seed_service in graph else 0,
            "seed_out_degree": graph.out_degree(request.seed_service) if request.seed_service in graph else 0,
        }

        return CascadeSimulationResponse(
            timestamp=datetime.now(timezone.utc),
            seed_service=request.seed_service,
            failure_type=request.failure_type,
            simulation=simulation,
            candidate_plans=plans,
            recommended_plan=recommended,
            graph_topology_summary=topology_summary,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cascade simulation failed: {str(e)}",
        )


@router.get(
    "/plans",
    response_model=List[InterceptionPlan],
    summary="Get candidate interception plans for a failing service",
)
async def get_interception_plans(
    seed_service: str = Query(default="payment-service", description="Failing service name"),
    failure_type: str = Query(default="latency_spike"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_or_system),
):
    """Retrieves ranked interception plans for a target service."""
    graph = await cascade_planner_service.build_topology_graph(db)
    simulation = cascade_planner_service.simulate_propagation(
        graph=graph,
        seed_service=seed_service,
        failure_type=failure_type,
    )
    return cascade_planner_service.generate_interception_plans(
        graph=graph,
        seed_service=seed_service,
        baseline_sim=simulation,
        db=db,
        user=current_user,
    )


@router.post(
    "/execute-plan",
    response_model=CascadeExecutePlanResponse,
    summary="Safely execute an authorized cascade interception plan",
)
async def execute_interception_plan(
    request: CascadeExecutePlanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Executes an interception plan under Autonomy Budget governance:
    - Enforces human approval sign-off for critical services or high-risk actions.
    - Dispatches playbooks via Ansible Semaphore.
    - Records immutable audit log entries.
    """
    try:
        result = await cascade_planner_service.execute_interception_plan(
            plan_id=request.plan_id,
            seed_service=request.seed_service,
            strategy=request.strategy,
            incident_id=request.incident_id,
            user=current_user,
            db=db,
            approval_notes=request.approval_notes,
        )
        return CascadeExecutePlanResponse(**result)
    except PermissionError as pe:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(pe),
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Interception execution failed: {str(e)}",
        )
