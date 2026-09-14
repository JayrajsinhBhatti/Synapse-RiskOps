"""
Synapse RiskOps - Runbook Schemas
=================================
Owner: Person 2 | Week: 4

Schemas for reusable remediation runbooks.
All remediation actions are simulated/safe for the academic project.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.prediction import FailureType


class RemediationMode(str, Enum):
    """Execution mode for a remediation action."""

    SIMULATED = "simulated"


class RunbookStep(BaseModel):
    """One reusable remediation step."""

    step_number: int = Field(..., ge=1)
    action: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    mode: RemediationMode = RemediationMode.SIMULATED


class Runbook(BaseModel):
    """Reusable remediation runbook for a failure type."""

    runbook_id: str
    failure_type: FailureType
    service: Optional[str] = None
    title: str
    description: str
    steps: List[RunbookStep]


class RunbookExecutionRequest(BaseModel):
    """Request to execute a runbook."""

    service: str = Field(..., min_length=1)
    failure_type: FailureType
    routing_decision: str
    routing_confidence: float = Field(..., ge=0, le=1)


class RemediationActionResult(BaseModel):
    """Result of one simulated remediation action."""

    action: str
    target: str
    status: str


class RunbookExecutionResponse(BaseModel):
    """Result returned after attempting runbook execution."""

    runbook_id: str
    service: str
    failure_type: FailureType
    routing_decision: str
    executed: bool
    status: str
    message: str
    actions_executed: List[RemediationActionResult]