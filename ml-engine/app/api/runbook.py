"""
Synapse RiskOps - Runbook API
=============================
Owner: Person 2 | Week: 4
"""

from typing import List

from fastapi import APIRouter, HTTPException, Query

from app.schemas.prediction import FailureType
from app.schemas.runbook import (
    Runbook,
    RunbookExecutionRequest,
    RunbookExecutionResponse,
)
from app.services.runbook_engine import runbook_engine


router = APIRouter(
    prefix="/api/runbooks",
    tags=["Runbooks"],
)


@router.get("", response_model=List[Runbook])
async def list_runbooks(
    failure_type: FailureType | None = Query(
        default=None,
        description="Optional failure type filter",
    ),
    service: str | None = Query(
        default=None,
        description="Optional service filter",
    ),
):
    """List available runbooks, optionally filtered by failure type."""

    if failure_type is not None:
        runbook = runbook_engine.get_runbook(
            failure_type=failure_type,
            service=service,
        )

        if runbook is None:
            raise HTTPException(
                status_code=404,
                detail=f"No runbook found for failure type '{failure_type.value}'.",
            )

        return [runbook]

    return runbook_engine.list_runbooks()


@router.get("/{failure_type}", response_model=Runbook)
async def get_runbook(
    failure_type: FailureType,
    service: str | None = Query(default=None),
):
    """Get one runbook by failure type."""

    runbook = runbook_engine.get_runbook(
        failure_type=failure_type,
        service=service,
    )

    if runbook is None:
        raise HTTPException(
            status_code=404,
            detail=f"No runbook found for '{failure_type.value}'.",
        )

    return runbook


@router.post("/execute", response_model=RunbookExecutionResponse)
async def execute_runbook(request: RunbookExecutionRequest):
    """
    Execute a runbook.

    Execution is simulated and only allowed when the routing decision
    is auto_remediate.
    """

    return runbook_engine.execute(
        service=request.service,
        failure_type=request.failure_type,
        routing_decision=request.routing_decision,
        routing_confidence=request.routing_confidence,
    )