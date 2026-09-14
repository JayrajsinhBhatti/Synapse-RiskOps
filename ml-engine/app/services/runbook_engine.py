"""
Synapse RiskOps - Runbook Engine
================================
Owner: Person 2 | Week: 4

Maps predicted failure types to reusable remediation runbooks.

IMPORTANT:
All actions are SIMULATED. This engine does not execute destructive
production operations.
"""

from typing import Dict, List, Optional

from app.schemas.prediction import FailureType
from app.schemas.runbook import (
    RemediationActionResult,
    Runbook,
    RunbookExecutionResponse,
    RunbookStep,
)


class RunbookEngine:
    """Library of reusable remediation runbooks."""

    def __init__(self):
        self._runbooks: Dict[FailureType, Runbook] = {}
        self._build_default_runbooks()

    def _build_default_runbooks(self) -> None:
        """Create the predefined Week 4 runbooks."""

        self._runbooks = {

            FailureType.CPU_SATURATION: Runbook(
                runbook_id="RB-CPU-001",
                failure_type=FailureType.CPU_SATURATION,
                title="CPU Saturation Recovery",
                description="Reduce CPU pressure and restore service capacity.",
                steps=[
                    RunbookStep(
                        step_number=1,
                        action="scale_horizontally",
                        description="Simulate adding service instances.",
                    ),
                    RunbookStep(
                        step_number=2,
                        action="increase_cpu_limit",
                        description="Simulate increasing the CPU resource limit.",
                    ),
                ],
            ),

            FailureType.MEMORY_EXHAUSTION: Runbook(
                runbook_id="RB-MEM-001",
                failure_type=FailureType.MEMORY_EXHAUSTION,
                title="Memory Exhaustion Recovery",
                description="Reduce memory pressure and restore available memory.",
                steps=[
                    RunbookStep(
                        step_number=1,
                        action="restart_unhealthy_instance",
                        description="Simulate restarting an unhealthy service instance.",
                    ),
                    RunbookStep(
                        step_number=2,
                        action="increase_memory_limit",
                        description="Simulate increasing the memory resource limit.",
                    ),
                ],
            ),

            FailureType.DISK_IO_BOTTLENECK: Runbook(
                runbook_id="RB-DISK-001",
                failure_type=FailureType.DISK_IO_BOTTLENECK,
                title="Disk I/O Bottleneck Recovery",
                description="Reduce disk I/O pressure.",
                steps=[
                    RunbookStep(
                        step_number=1,
                        action="reduce_disk_queue",
                        description="Simulate reducing queued disk operations.",
                    ),
                    RunbookStep(
                        step_number=2,
                        action="scale_storage_capacity",
                        description="Simulate increasing storage capacity.",
                    ),
                ],
            ),

            FailureType.LATENCY_DEGRADATION: Runbook(
                runbook_id="RB-LATENCY-001",
                failure_type=FailureType.LATENCY_DEGRADATION,
                title="Latency Degradation Recovery",
                description="Reduce service response latency.",
                steps=[
                    RunbookStep(
                        step_number=1,
                        action="scale_service",
                        description="Simulate scaling the affected service.",
                    ),
                    RunbookStep(
                        step_number=2,
                        action="enable_cache",
                        description="Simulate enabling an appropriate cache layer.",
                    ),
                ],
            ),

            FailureType.ERROR_RATE_SPIKE: Runbook(
                runbook_id="RB-ERROR-001",
                failure_type=FailureType.ERROR_RATE_SPIKE,
                title="Error Rate Spike Recovery",
                description="Reduce elevated application error rates.",
                steps=[
                    RunbookStep(
                        step_number=1,
                        action="restart_unhealthy_instance",
                        description="Simulate restarting an unhealthy instance.",
                    ),
                    RunbookStep(
                        step_number=2,
                        action="route_traffic_to_healthy_instance",
                        description="Simulate routing traffic away from an unhealthy instance.",
                    ),
                ],
            ),

            FailureType.CONNECTION_POOL_EXHAUSTION: Runbook(
                runbook_id="RB-CONN-001",
                failure_type=FailureType.CONNECTION_POOL_EXHAUSTION,
                title="Connection Pool Recovery",
                description="Restore available service/database connections.",
                steps=[
                    RunbookStep(
                        step_number=1,
                        action="increase_connection_pool",
                        description="Simulate increasing the connection pool capacity.",
                    ),
                    RunbookStep(
                        step_number=2,
                        action="release_idle_connections",
                        description="Simulate releasing idle connections.",
                    ),
                ],
            ),

            FailureType.CASCADING_FAILURE: Runbook(
                runbook_id="RB-CASCADE-001",
                failure_type=FailureType.CASCADING_FAILURE,
                title="Cascading Failure Containment",
                description="Contain propagation across dependent services.",
                steps=[
                    RunbookStep(
                        step_number=1,
                        action="isolate_affected_service",
                        description="Simulate isolating the affected service.",
                    ),
                    RunbookStep(
                        step_number=2,
                        action="reroute_traffic",
                        description="Simulate rerouting traffic around the affected service.",
                    ),
                ],
            ),
        }

    def list_runbooks(self) -> List[Runbook]:
        """Return all available runbooks."""
        return list(self._runbooks.values())

    def get_runbook(
        self,
        failure_type: FailureType,
        service: Optional[str] = None,
    ) -> Optional[Runbook]:
        """
        Return the runbook for a failure type.

        Service is currently metadata used by the API. The runbook itself
        is reusable across services.
        """
        return self._runbooks.get(failure_type)

    def execute(
        self,
        service: str,
        failure_type: FailureType,
        routing_decision: str,
        routing_confidence: float,
    ) -> RunbookExecutionResponse:
        """
        Execute a runbook only when routing approved auto-remediation.

        Actual operations are simulated.
        """

        runbook = self.get_runbook(failure_type)

        if runbook is None:
            return RunbookExecutionResponse(
                runbook_id="NONE",
                service=service,
                failure_type=failure_type,
                routing_decision=routing_decision,
                executed=False,
                status="NO_RUNBOOK",
                message="No runbook exists for this failure type.",
                actions_executed=[],
            )

        if routing_decision != "auto_remediate":
            return RunbookExecutionResponse(
                runbook_id=runbook.runbook_id,
                service=service,
                failure_type=failure_type,
                routing_decision=routing_decision,
                executed=False,
                status="NOT_EXECUTED",
                message=(
                    f"Routing decision is '{routing_decision}'. "
                    "Remediation requires auto_remediate."
                ),
                actions_executed=[],
            )

        actions = [
            RemediationActionResult(
                action=step.action,
                target=service,
                status="simulated_success",
            )
            for step in runbook.steps
        ]

        return RunbookExecutionResponse(
            runbook_id=runbook.runbook_id,
            service=service,
            failure_type=failure_type,
            routing_decision=routing_decision,
            executed=True,
            status="SUCCESS",
            message=(
                f"Simulated execution completed for {service} "
                f"using {runbook.runbook_id}."
            ),
            actions_executed=actions,
        )


# Singleton used by the FastAPI router.
runbook_engine = RunbookEngine()