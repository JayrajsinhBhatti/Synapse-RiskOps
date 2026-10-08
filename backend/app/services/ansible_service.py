"""
Synapse RiskOps - Ansible Semaphore Integration Service
========================================================
Owner: Person 2 | Week: 6
Triggers real Ansible playbooks via the Semaphore REST API (http://localhost:3000/api)
and records execution history at http://localhost:3000/project/1/history
"""

import json
import logging
from typing import Any, Dict, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger("synapse.ansible")

TEMPLATE_MAPPING = {
    # Scale Resources (template_id: 2 -> scale_resources.yml)
    "SCALE_OUT_PODS": 2,
    "SCALE_SERVICE": 2,
    "SCALE_RESOURCES": 2,
    "scale_resources": 2,
    "scale_out_pods": 2,
    "memory_leak": 2,
    "high_cpu": 2,
    "latency_degradation": 2,
    "RATE_LIMIT_GATEWAY": 2,
    "rate_limit_gateway": 2,

    # Restart Service (template_id: 1 -> restart_service.yml)
    "RESTART_SERVICE": 1,
    "RESTART_POD": 1,
    "restart_service": 1,
    "restart_pod": 1,
    "service_crash": 1,
    "connection_pool_exhaustion": 1,
    "cascading_failure": 1,
    "DRAIN_TRAFFIC": 1,

    # Clear Disk / Flush Cache (template_id: 3 -> clear_disk.yml)
    "CLEAR_DISK": 3,
    "FLUSH_REDIS_CACHE": 3,
    "clear_disk": 3,
    "flush_redis_cache": 3,
    "disk_exhaustion": 3,

    # Reset Network / Circuit Breaker (template_id: 4 -> reset_network.yml)
    "RESET_NETWORK": 4,
    "CIRCUIT_BREAKER_TRIP": 4,
    "reset_network": 4,
    "circuit_breaker_trip": 4,
    "network_degradation": 4,
}


class AnsibleService:
    """Dispatches Ansible remediation playbooks into Semaphore Project 1."""

    def __init__(self):
        self.base_url = getattr(settings, "SEMAPHORE_URL", "http://localhost:3000").rstrip("/")
        self.api_token = getattr(settings, "SEMAPHORE_API_TOKEN", "hegkfuqjxkcud_yz0fngh-1o6rrifhvqwl3yi9cvzje=")
        self.project_id = getattr(settings, "SEMAPHORE_PROJECT_ID", 1)
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_token}",
        }

    async def trigger_remediation_task(
        self,
        action: str,
        service_name: str,
        incident_id: str,
        failure_type: str = "latency_degradation",
        risk_score: float = 85.0,
        target_host: str = "synapse-cluster",
    ) -> Dict[str, Any]:
        """
        Launches an Ansible Playbook task in Semaphore (Project 1).
        This guarantees the task and full execution logs appear in:
        http://localhost:3000/project/1/history
        """
        template_id = TEMPLATE_MAPPING.get(action) or TEMPLATE_MAPPING.get(failure_type) or 2

        env_payload = json.dumps({
            "action": action.lower(),
            "service_name": service_name,
            "failure_type": failure_type,
            "risk_score": float(risk_score),
            "target_host": target_host,
            "incident_id": str(incident_id),
        })

        payload = {
            "template_id": template_id,
            "environment": env_payload,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/project/{self.project_id}/tasks",
                    headers=self.headers,
                    json=payload,
                )
                if resp.status_code in (200, 201):
                    task_data = resp.json()
                    task_id = task_data.get("id")
                    logger.info(f"[Ansible] Successfully launched Semaphore task #{task_id} for incident {incident_id}")
                    return {
                        "status": "LAUNCHED",
                        "task_id": task_id,
                        "template_id": template_id,
                        "semaphore_history_url": f"{self.base_url}/project/{self.project_id}/history",
                        "task_url": f"{self.base_url}/project/{self.project_id}/tasks/{task_id}",
                    }
                else:
                    logger.warning(f"[Ansible] Semaphore API returned {resp.status_code}: {resp.text}")
                    return {
                        "status": "FAILED",
                        "task_id": None,
                        "detail": resp.text,
                        "semaphore_history_url": f"{self.base_url}/project/{self.project_id}/history",
                    }
        except Exception as e:
            logger.error(f"[Ansible] Failed to communicate with Semaphore API at {self.base_url}: {e}")
            return {
                "status": "FAILED",
                "task_id": None,
                "error": str(e),
                "semaphore_history_url": f"{self.base_url}/project/{self.project_id}/history",
            }


ansible_service = AnsibleService()
