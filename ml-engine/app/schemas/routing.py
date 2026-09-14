"""
Synapse RiskOps - Routing Schemas
=================================
Owner: Person 2 | Week: 4

Data models for receiving and storing Person 1's confidence-routing decisions.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RoutingDecisionRequest(BaseModel):
    """Routing decision received from the GenAI agent."""

    incident_id: str = Field(..., min_length=1)
    service: str = Field(..., min_length=1)

    routing_decision: str = Field(
        ...,
        pattern="^(auto_remediate|escalate)$",
    )

    routing_confidence: float = Field(
        ...,
        ge=0,
        le=1,
    )

    routing_threshold_used: float = Field(
        ...,
        ge=0,
        le=1,
    )

    human_override: bool = False

    human_override_reason: Optional[str] = None

    was_routing_correct: Optional[bool] = None


class RoutingDecisionRecord(RoutingDecisionRequest):
    """Stored routing decision with timestamp."""

    recorded_at: str


class RoutingDecisionResponse(BaseModel):
    """Response after recording a routing decision."""

    status: str
    decision: RoutingDecisionRecord


class RoutingHistoryResponse(BaseModel):
    """Routing history for a service."""

    service: str
    total_decisions: int
    decisions: List[RoutingDecisionRecord]