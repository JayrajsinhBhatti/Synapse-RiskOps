"""
genai-agent/app/remediation/ansible_executor.py

Programmatic Ansible remediation via the Semaphore API.
Maps failure types to Ansible playbook template IDs and triggers
execution through the Semaphore REST API, then polls for completion.

Integrates with the LangGraph pipeline as a remediation node.
"""

import os
import time
from enum import Enum
from typing import Dict, Optional

import httpx
from loguru import logger


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SEMAPHORE_URL = os.getenv("SEMAPHORE_URL", "http://semaphore:3000")
SEMAPHORE_API_TOKEN = os.getenv(
    "SEMAPHORE_API_TOKEN",
    "hegkfuqjxkcud_yz0fngh-1o6rrifhvqwl3yi9cvzje=",
)
SEMAPHORE_PROJECT_ID = int(os.getenv("SEMAPHORE_PROJECT_ID", "1"))


# ---------------------------------------------------------------------------
# Failure → Playbook mapping
# ---------------------------------------------------------------------------
class PlaybookTemplate(Enum):
    """Maps failure types to Semaphore template IDs (set in Semaphore UI)."""
    RESTART_SERVICE = 1
    SCALE_RESOURCES = 2
    CLEAR_DISK = 3
    RESET_NETWORK = 4
    HEALTH_CHECK = 5


FAILURE_TO_PLAYBOOK: Dict[str, PlaybookTemplate] = {
    "service_crash": PlaybookTemplate.RESTART_SERVICE,
    "memory_leak": PlaybookTemplate.SCALE_RESOURCES,
    "disk_exhaustion": PlaybookTemplate.CLEAR_DISK,
    "network_degradation": PlaybookTemplate.RESET_NETWORK,
    "high_cpu": PlaybookTemplate.SCALE_RESOURCES,
    "connection_pool_exhaustion": PlaybookTemplate.RESTART_SERVICE,
    "gc_pressure": PlaybookTemplate.RESTART_SERVICE,
    "cascading_failure": PlaybookTemplate.RESTART_SERVICE,
}


# ---------------------------------------------------------------------------
# Semaphore API Client
# ---------------------------------------------------------------------------
class AnsibleExecutor:
    """
    Triggers Ansible playbooks through the Semaphore REST API and tracks
    execution status.
    """

    def __init__(
        self,
        base_url: str = SEMAPHORE_URL,
        api_token: str = SEMAPHORE_API_TOKEN,
        project_id: int = SEMAPHORE_PROJECT_ID,
    ):
        self.base_url = base_url.rstrip("/")
        self.project_id = project_id
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_token}",
        }

    # ----- public interface -----

    async def execute_remediation(
        self,
        failure_type: str,
        service_name: str,
        incident_id: str,
        risk_score: float,
        target_host: str = "synapse-cluster",
    ) -> Dict:
        """
        Run the appropriate Ansible playbook for the given failure type.

        Returns a result dict with keys:
          status   – "SUCCESS" | "FAILED" | "TIMEOUT"
          task_id  – Semaphore task ID
          duration – wall-clock seconds
          output   – last status message
        """
        template = FAILURE_TO_PLAYBOOK.get(failure_type)
        if template is None:
            logger.warning(
                f"No playbook mapped for failure_type={failure_type}. Skipping."
            )
            return {
                "status": "SKIPPED",
                "task_id": None,
                "duration": 0,
                "output": f"No playbook for failure_type '{failure_type}'",
            }

        environment_json = (
            f'{{"action":"{template.name.lower()}",'
            f'"service_name":"{service_name}",'
            f'"failure_type":"{failure_type}",'
            f'"risk_score":{risk_score},'
            f'"target_host":"{target_host}",'
            f'"incident_id":"{incident_id}"}}'
        )

        payload = {
            "template_id": template.value,
            "environment": environment_json,
        }

        logger.info(
            f"[Ansible] Triggering playbook {template.name} "
            f"(template_id={template.value}) for {service_name}"
        )

        start = time.monotonic()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 1. Launch task
                resp = await client.post(
                    f"{self.base_url}/api/project/{self.project_id}/tasks",
                    headers=self.headers,
                    json=payload,
                )
                resp.raise_for_status()
                task = resp.json()
                task_id = task.get("id")

                logger.info(f"[Ansible] Task {task_id} started")

                # 2. Poll for completion (max 120 s)
                status = await self._poll_task(client, task_id, timeout=120)

                duration = round(time.monotonic() - start, 2)
                return {
                    "status": status,
                    "task_id": task_id,
                    "duration": duration,
                    "output": f"Playbook {template.name} completed with status {status}",
                }

        except Exception as exc:
            duration = round(time.monotonic() - start, 2)
            logger.error(f"[Ansible] Execution failed: {exc}")
            return {
                "status": "FAILED",
                "task_id": None,
                "duration": duration,
                "output": str(exc),
            }

    async def run_health_check(self, service_name: str) -> Dict:
        """Run the post-remediation health-check playbook."""
        environment_json = (
            f'{{"action":"health_check","service_name":"{service_name}"}}'
        )
        payload = {
            "template_id": PlaybookTemplate.HEALTH_CHECK.value,
            "environment": environment_json,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/project/{self.project_id}/tasks",
                    headers=self.headers,
                    json=payload,
                )
                resp.raise_for_status()
                task = resp.json()
                task_id = task.get("id")

                status = await self._poll_task(client, task_id, timeout=60)
                return {"status": status, "task_id": task_id}
        except Exception as exc:
            logger.error(f"[Ansible] Health check failed: {exc}")
            return {"status": "FAILED", "task_id": None, "error": str(exc)}

    # ----- internal helpers -----

    async def _poll_task(
        self,
        client: httpx.AsyncClient,
        task_id: int,
        timeout: int = 120,
        interval: int = 3,
    ) -> str:
        """
        Poll Semaphore task status until completion or timeout.
        Returns "SUCCESS", "FAILED", or "TIMEOUT".
        """
        import asyncio

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                resp = await client.get(
                    f"{self.base_url}/api/project/{self.project_id}/tasks/{task_id}",
                    headers=self.headers,
                )
                resp.raise_for_status()
                task = resp.json()
                status = task.get("status", "")

                if status == "success":
                    return "SUCCESS"
                elif status in ("error", "stopped"):
                    return "FAILED"

            except Exception as exc:
                logger.warning(f"[Ansible] Poll error for task {task_id}: {exc}")

            await asyncio.sleep(interval)

        logger.warning(f"[Ansible] Task {task_id} timed out after {timeout}s")
        return "TIMEOUT"


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_executor: Optional[AnsibleExecutor] = None


def get_ansible_executor() -> AnsibleExecutor:
    global _executor
    if _executor is None:
        _executor = AnsibleExecutor()
    return _executor
