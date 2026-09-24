"""
runbooks/engine.py

Runbook execution engine for Synapse RiskOps.
Loads YAML runbook definitions, validates them against the schema,
and executes steps sequentially using the appropriate remediation
executor (Docker SDK, Ansible, Kubernetes, HTTP).

Integrates with the LangGraph pipeline as the remediation orchestrator.
"""

import os
import sys
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from loguru import logger


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
RUNBOOKS_DIR = Path(__file__).parent / "definitions"


class RunbookStep:
    """Represents a single step in a runbook."""

    def __init__(self, definition: Dict):
        self.name = definition["name"]
        self.executor = definition["executor"]
        self.action = definition["action"]
        self.params = definition.get("params", {})
        self.timeout = definition.get("timeout_seconds", 60)
        self.on_failure = definition.get("on_failure", "escalate")
        self.condition = definition.get("condition")

    def __repr__(self):
        return f"<Step: {self.name} ({self.executor}.{self.action})>"


class Runbook:
    """Represents a complete runbook definition."""

    def __init__(self, definition: Dict, source_file: str = ""):
        self.name = definition["name"]
        self.description = definition.get("description", "")
        self.failure_types = definition.get("failure_types", [])
        self.severity = definition.get("severity", "high")
        self.auto_trigger = definition.get("auto_trigger", True)
        self.max_execution_time = definition.get(
            "max_execution_time_seconds", 300
        )
        self.steps = [RunbookStep(s) for s in definition.get("steps", [])]
        self.rollback_steps = [
            RunbookStep(s) for s in definition.get("rollback_steps", [])
        ]
        self.source_file = source_file

    def __repr__(self):
        return (
            f"<Runbook: {self.name} "
            f"({len(self.steps)} steps, "
            f"triggers={self.failure_types})>"
        )


class StepResult:
    """Result of executing a single runbook step."""

    def __init__(
        self,
        step_name: str,
        status: str,
        duration: float,
        output: Optional[Dict] = None,
        error: Optional[str] = None,
    ):
        self.step_name = step_name
        self.status = status  # SUCCESS, FAILED, SKIPPED
        self.duration = duration
        self.output = output or {}
        self.error = error

    def to_dict(self) -> Dict:
        return {
            "step": self.step_name,
            "status": self.status,
            "duration_seconds": self.duration,
            "output": self.output,
            "error": self.error,
        }


class RunbookEngine:
    """
    Loads and executes runbooks.
    Maps runbook steps to the appropriate remediation executor.
    """

    def __init__(self, runbooks_dir: Optional[Path] = None):
        self.runbooks_dir = runbooks_dir or RUNBOOKS_DIR
        self.runbooks: Dict[str, Runbook] = {}
        self._load_runbooks()

    def _load_runbooks(self):
        """Load all YAML runbook definitions from the definitions directory."""
        if not self.runbooks_dir.exists():
            logger.warning(
                f"[RunbookEngine] Runbooks directory not found: {self.runbooks_dir}"
            )
            return

        for yml_file in self.runbooks_dir.glob("*.yml"):
            try:
                with open(yml_file, "r") as f:
                    definition = yaml.safe_load(f)

                if definition is None:
                    continue

                runbook = Runbook(definition, source_file=str(yml_file))

                # Index by each failure type
                for ft in runbook.failure_types:
                    self.runbooks[ft] = runbook

                logger.info(
                    f"[RunbookEngine] Loaded: {runbook.name} "
                    f"(triggers: {runbook.failure_types})"
                )
            except Exception as exc:
                logger.error(
                    f"[RunbookEngine] Failed to load {yml_file}: {exc}"
                )

        logger.info(
            f"[RunbookEngine] {len(self.runbooks)} failure-type mappings loaded"
        )

    def get_runbook(self, failure_type: str) -> Optional[Runbook]:
        """Get the runbook for a given failure type."""
        return self.runbooks.get(failure_type)

    def list_runbooks(self) -> List[Dict]:
        """List all loaded runbooks with metadata."""
        seen = set()
        result = []
        for runbook in self.runbooks.values():
            if runbook.name not in seen:
                seen.add(runbook.name)
                result.append({
                    "name": runbook.name,
                    "description": runbook.description,
                    "failure_types": runbook.failure_types,
                    "severity": runbook.severity,
                    "auto_trigger": runbook.auto_trigger,
                    "step_count": len(runbook.steps),
                    "source_file": runbook.source_file,
                })
        return result

    async def execute(
        self,
        failure_type: str,
        service_name: str,
        incident_id: str = "",
        risk_score: float = 0.0,
        dry_run: bool = False,
    ) -> Dict:
        """
        Execute the runbook for a given failure type.

        Args:
            failure_type: Type of failure to remediate
            service_name: Name of the affected service
            incident_id: Incident reference ID
            risk_score: Current risk score
            dry_run: If True, log steps without executing

        Returns:
            Execution result dict with status and step results.
        """
        runbook = self.get_runbook(failure_type)
        if runbook is None:
            return {
                "status": "NO_RUNBOOK",
                "failure_type": failure_type,
                "message": f"No runbook defined for '{failure_type}'",
            }

        if not runbook.auto_trigger:
            return {
                "status": "MANUAL_ONLY",
                "runbook": runbook.name,
                "message": "Runbook requires manual trigger. Escalating.",
            }

        logger.info(
            f"[RunbookEngine] Executing: {runbook.name} "
            f"for {service_name} (incident={incident_id})"
        )

        start = time.monotonic()
        step_results: List[StepResult] = []
        overall_status = "SUCCESS"

        for step in runbook.steps:
            if dry_run:
                step_results.append(
                    StepResult(step.name, "DRY_RUN", 0.0)
                )
                logger.info(f"  [DRY RUN] {step.name}")
                continue

            step_start = time.monotonic()
            try:
                result = await self._execute_step(
                    step, service_name, incident_id, risk_score
                )
                step_duration = round(time.monotonic() - step_start, 2)

                step_status = result.get("status", "UNKNOWN")
                step_results.append(
                    StepResult(
                        step.name, step_status, step_duration, output=result
                    )
                )

                logger.info(
                    f"  [{step_status}] {step.name} ({step_duration}s)"
                )

                if step_status == "FAILED":
                    if step.on_failure == "abort":
                        overall_status = "ABORTED"
                        break
                    elif step.on_failure == "escalate":
                        overall_status = "ESCALATED"
                        break
                    elif step.on_failure == "rollback":
                        overall_status = "ROLLED_BACK"
                        await self._execute_rollback(
                            runbook, service_name, incident_id, risk_score
                        )
                        break
                    # "continue" — keep going

            except Exception as exc:
                step_duration = round(time.monotonic() - step_start, 2)
                step_results.append(
                    StepResult(
                        step.name, "ERROR", step_duration, error=str(exc)
                    )
                )
                logger.error(f"  [ERROR] {step.name}: {exc}")

                if step.on_failure != "continue":
                    overall_status = "ESCALATED"
                    break

        total_duration = round(time.monotonic() - start, 2)

        return {
            "status": overall_status,
            "runbook": runbook.name,
            "failure_type": failure_type,
            "service_name": service_name,
            "incident_id": incident_id,
            "total_duration_seconds": total_duration,
            "steps_executed": len(step_results),
            "steps_total": len(runbook.steps),
            "step_results": [sr.to_dict() for sr in step_results],
        }

    async def _execute_step(
        self,
        step: RunbookStep,
        service_name: str,
        incident_id: str,
        risk_score: float,
    ) -> Dict:
        """Execute a single runbook step using the appropriate executor."""

        if step.executor == "docker":
            return await self._exec_docker(step, service_name)
        elif step.executor == "ansible":
            return await self._exec_ansible(
                step, service_name, incident_id, risk_score
            )
        elif step.executor == "kubernetes":
            return await self._exec_kubernetes(step, service_name)
        elif step.executor == "script":
            return await self._exec_script(step)
        elif step.executor == "http":
            return await self._exec_http(step, service_name)
        else:
            return {"status": "FAILED", "error": f"Unknown executor: {step.executor}"}

    async def _exec_docker(self, step: RunbookStep, service_name: str) -> Dict:
        """Execute a Docker SDK step."""
        try:
            from genai_agent_remediation import get_docker_healer
        except ImportError:
            try:
                # Fallback import path when running within the genai-agent
                from app.remediation.docker_healer import get_docker_healer
            except ImportError:
                return {"status": "FAILED", "error": "Docker healer not available"}

        healer = get_docker_healer()
        container_name = f"synapse-{service_name}"

        action_map = {
            "restart_container": lambda: healer.restart_container(
                container_name, **step.params
            ),
            "update_resources": lambda: healer.update_resources(
                container_name, **step.params
            ),
            "inspect_health": lambda: healer.inspect_health(container_name),
            "get_logs": lambda: healer.get_container_logs(
                container_name, **step.params
            ),
            "fix_network": lambda: healer.fix_network(
                container_name, **step.params
            ),
            "prune_system": lambda: healer.prune_system(),
        }

        action = action_map.get(step.action)
        if action is None:
            return {"status": "FAILED", "error": f"Unknown docker action: {step.action}"}

        return action()

    async def _exec_ansible(
        self, step: RunbookStep, service_name: str,
        incident_id: str, risk_score: float,
    ) -> Dict:
        """Execute an Ansible step via Semaphore API."""
        try:
            from app.remediation.ansible_executor import get_ansible_executor
        except ImportError:
            return {"status": "FAILED", "error": "Ansible executor not available"}

        executor = get_ansible_executor()

        if step.action == "health_check":
            return await executor.run_health_check(service_name)
        else:
            return await executor.execute_remediation(
                failure_type=step.action,
                service_name=service_name,
                incident_id=incident_id,
                risk_score=risk_score,
            )

    async def _exec_kubernetes(self, step: RunbookStep, service_name: str) -> Dict:
        """Execute a Kubernetes step."""
        try:
            from app.remediation.k8s_healer import get_k8s_healer
        except ImportError:
            return {"status": "FAILED", "error": "K8s healer not available"}

        healer = get_k8s_healer()
        return healer.remediate(step.action, service_name)

    async def _exec_script(self, step: RunbookStep) -> Dict:
        """Execute a script step (e.g., sleep)."""
        if step.action == "sleep":
            seconds = step.params.get("seconds", 5)
            await asyncio.sleep(seconds)
            return {"status": "SUCCESS", "slept_seconds": seconds}
        return {"status": "FAILED", "error": f"Unknown script action: {step.action}"}

    async def _exec_http(self, step: RunbookStep, service_name: str) -> Dict:
        """Execute an HTTP request step."""
        import httpx

        url = step.params.get("url", "")
        query_param = step.params.get("query_param")
        if query_param:
            url = f"{url}?{query_param}={service_name}"

        try:
            async with httpx.AsyncClient(timeout=step.timeout) as client:
                resp = await client.get(url)
                return {
                    "status": "SUCCESS" if resp.status_code < 400 else "FAILED",
                    "http_status": resp.status_code,
                    "body": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text[:500],
                }
        except Exception as exc:
            return {"status": "FAILED", "error": str(exc)}

    async def _execute_rollback(
        self, runbook: Runbook, service_name: str,
        incident_id: str, risk_score: float,
    ):
        """Execute rollback steps if defined."""
        if not runbook.rollback_steps:
            return
        logger.warning(f"[RunbookEngine] Executing rollback for {runbook.name}")
        for step in runbook.rollback_steps:
            try:
                await self._execute_step(step, service_name, incident_id, risk_score)
            except Exception as exc:
                logger.error(f"[RunbookEngine] Rollback step failed: {exc}")

    def validate(self) -> List[Dict]:
        """
        Validate all loaded runbooks.
        Returns list of validation errors (empty = all valid).
        """
        errors = []
        valid_executors = {"docker", "ansible", "kubernetes", "http", "script"}

        for yml_file in self.runbooks_dir.glob("*.yml"):
            try:
                with open(yml_file, "r") as f:
                    definition = yaml.safe_load(f)

                if not definition:
                    errors.append({"file": str(yml_file), "error": "Empty file"})
                    continue

                # Check required fields
                for field in ["name", "failure_types", "steps"]:
                    if field not in definition:
                        errors.append({
                            "file": str(yml_file),
                            "error": f"Missing required field: {field}",
                        })

                # Check steps
                for i, step in enumerate(definition.get("steps", [])):
                    if "name" not in step:
                        errors.append({
                            "file": str(yml_file),
                            "error": f"Step {i}: missing 'name'",
                        })
                    if step.get("executor") not in valid_executors:
                        errors.append({
                            "file": str(yml_file),
                            "error": f"Step {i}: invalid executor '{step.get('executor')}'",
                        })

            except Exception as exc:
                errors.append({"file": str(yml_file), "error": str(exc)})

        return errors


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_engine: Optional[RunbookEngine] = None


def get_runbook_engine() -> RunbookEngine:
    global _engine
    if _engine is None:
        _engine = RunbookEngine()
    return _engine


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    engine = RunbookEngine()

    if "--validate" in sys.argv:
        errors = engine.validate()
        if errors:
            print(f"\n[ERROR] Validation found {len(errors)} error(s):")
            for err in errors:
                print(f"  - {err['file']}: {err['error']}")
            sys.exit(1)
        else:
            print(f"\n[OK] All runbooks valid ({len(engine.list_runbooks())} loaded)")
            sys.exit(0)

    print("\nLoaded Runbooks:")
    for rb in engine.list_runbooks():
        print(f"  [{rb['severity'].upper():8s}] {rb['name']}")
        print(f"             Triggers: {', '.join(rb['failure_types'])}")
        print(f"             Steps: {rb['step_count']}, Auto: {rb['auto_trigger']}")
        print()
