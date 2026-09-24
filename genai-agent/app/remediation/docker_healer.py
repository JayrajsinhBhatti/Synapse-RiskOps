"""
genai-agent/app/remediation/docker_healer.py

Programmatic container remediation using the Docker Python SDK.
Provides fast, in-process container operations (restart, scale,
prune, network fix) without shelling out to Ansible.

Used by the LangGraph remediation node for quick container-level
fixes before falling back to Ansible for complex multi-step ops.
"""

import time
from typing import Dict, List, Optional

import docker
from docker.errors import DockerException, NotFound, APIError
from loguru import logger


class DockerHealer:
    """
    Docker SDK-based remediation executor.
    Connects to the Docker daemon via socket and performs
    container-level fixes programmatically.
    """

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize Docker client.
        Uses the default socket (/var/run/docker.sock) unless overridden.
        """
        try:
            if base_url:
                self.client = docker.DockerClient(base_url=base_url)
            else:
                self.client = docker.from_env()
            self._connected = True
            logger.info("[DockerHealer] Connected to Docker daemon")
        except DockerException as exc:
            self._connected = False
            self.client = None
            logger.error(f"[DockerHealer] Failed to connect: {exc}")

    @property
    def is_connected(self) -> bool:
        return self._connected

    def test_connection(self) -> bool:
        """Verify Docker daemon connectivity."""
        try:
            return self.client.ping() if self.client else False
        except Exception:
            return False

    # -----------------------------------------------------------------
    # Container operations
    # -----------------------------------------------------------------

    def restart_container(
        self, container_name: str, timeout: int = 30
    ) -> Dict:
        """
        Restart a container by name.
        Returns status dict with before/after state.
        """
        start = time.monotonic()
        try:
            container = self.client.containers.get(container_name)
            state_before = container.status

            container.restart(timeout=timeout)
            container.reload()

            duration = round(time.monotonic() - start, 2)
            logger.info(
                f"[DockerHealer] Restarted {container_name} "
                f"({state_before} → {container.status}) in {duration}s"
            )
            return {
                "action": "restart",
                "container": container_name,
                "status": "SUCCESS",
                "state_before": state_before,
                "state_after": container.status,
                "duration_seconds": duration,
            }
        except NotFound:
            return self._error_result("restart", container_name, "Container not found")
        except APIError as exc:
            return self._error_result("restart", container_name, str(exc))

    def update_resources(
        self,
        container_name: str,
        mem_limit: Optional[str] = None,
        cpu_quota: Optional[int] = None,
        cpu_period: Optional[int] = None,
    ) -> Dict:
        """
        Update container resource limits (memory, CPU).

        Args:
            mem_limit: e.g. "2g", "512m"
            cpu_quota: microseconds of CPU time per cpu_period
            cpu_period: CPU CFS period (default 100000 = 100ms)
        """
        start = time.monotonic()
        try:
            container = self.client.containers.get(container_name)
            update_kwargs = {}
            if mem_limit:
                update_kwargs["mem_limit"] = mem_limit
                update_kwargs["memswap_limit"] = mem_limit
            if cpu_quota is not None:
                update_kwargs["cpu_quota"] = cpu_quota
            if cpu_period is not None:
                update_kwargs["cpu_period"] = cpu_period

            if not update_kwargs:
                return self._error_result(
                    "update_resources", container_name, "No resource params specified"
                )

            container.update(**update_kwargs)
            duration = round(time.monotonic() - start, 2)

            logger.info(
                f"[DockerHealer] Updated resources for {container_name}: "
                f"{update_kwargs} in {duration}s"
            )
            return {
                "action": "update_resources",
                "container": container_name,
                "status": "SUCCESS",
                "applied": update_kwargs,
                "duration_seconds": duration,
            }
        except NotFound:
            return self._error_result("update_resources", container_name, "Container not found")
        except APIError as exc:
            return self._error_result("update_resources", container_name, str(exc))

    def get_container_logs(
        self, container_name: str, tail: int = 100
    ) -> Dict:
        """Fetch recent container logs for post-incident analysis."""
        try:
            container = self.client.containers.get(container_name)
            logs = container.logs(tail=tail, timestamps=True).decode(
                "utf-8", errors="replace"
            )
            return {
                "action": "get_logs",
                "container": container_name,
                "status": "SUCCESS",
                "log_lines": logs.splitlines(),
                "line_count": len(logs.splitlines()),
            }
        except NotFound:
            return self._error_result("get_logs", container_name, "Container not found")
        except APIError as exc:
            return self._error_result("get_logs", container_name, str(exc))

    def inspect_health(self, container_name: str) -> Dict:
        """
        Inspect container health status.
        Returns detailed state including health check results.
        """
        try:
            container = self.client.containers.get(container_name)
            attrs = container.attrs
            state = attrs.get("State", {})
            health = state.get("Health", {})

            return {
                "action": "inspect_health",
                "container": container_name,
                "status": "SUCCESS",
                "container_status": state.get("Status", "unknown"),
                "running": state.get("Running", False),
                "exit_code": state.get("ExitCode", -1),
                "started_at": state.get("StartedAt", ""),
                "health_status": health.get("Status", "none"),
                "health_failing_streak": health.get("FailingStreak", 0),
                "restart_count": attrs.get("RestartCount", 0),
            }
        except NotFound:
            return self._error_result("inspect_health", container_name, "Container not found")
        except APIError as exc:
            return self._error_result("inspect_health", container_name, str(exc))

    def fix_network(
        self,
        container_name: str,
        network_name: str = "synapse-riskops-network",
    ) -> Dict:
        """
        Disconnect and reconnect a container to the Docker network
        to resolve networking issues.
        """
        start = time.monotonic()
        try:
            network = self.client.networks.get(network_name)

            # Disconnect (ignore errors if not connected)
            try:
                network.disconnect(container_name, force=True)
                logger.info(f"[DockerHealer] Disconnected {container_name} from {network_name}")
            except APIError:
                pass

            # Reconnect
            network.connect(container_name)
            duration = round(time.monotonic() - start, 2)

            logger.info(
                f"[DockerHealer] Reconnected {container_name} to "
                f"{network_name} in {duration}s"
            )
            return {
                "action": "fix_network",
                "container": container_name,
                "network": network_name,
                "status": "SUCCESS",
                "duration_seconds": duration,
            }
        except NotFound as exc:
            return self._error_result("fix_network", container_name, f"Not found: {exc}")
        except APIError as exc:
            return self._error_result("fix_network", container_name, str(exc))

    def prune_system(self) -> Dict:
        """
        Prune unused Docker resources (containers, images, volumes)
        to free disk space.
        """
        start = time.monotonic()
        results = {}

        try:
            results["containers"] = self.client.containers.prune()
            results["images"] = self.client.images.prune()
            results["volumes"] = self.client.volumes.prune()

            duration = round(time.monotonic() - start, 2)
            space_reclaimed = sum(
                r.get("SpaceReclaimed", 0)
                for r in results.values()
                if isinstance(r, dict)
            )

            logger.info(
                f"[DockerHealer] Pruned system: {space_reclaimed / 1024 / 1024:.1f} MB "
                f"reclaimed in {duration}s"
            )
            return {
                "action": "prune_system",
                "status": "SUCCESS",
                "space_reclaimed_bytes": space_reclaimed,
                "space_reclaimed_mb": round(space_reclaimed / 1024 / 1024, 1),
                "details": {k: str(v) for k, v in results.items()},
                "duration_seconds": duration,
            }
        except APIError as exc:
            return self._error_result("prune_system", "all", str(exc))

    def list_containers(self, name_prefix: str = "synapse-") -> List[Dict]:
        """List all Synapse containers and their status."""
        try:
            containers = self.client.containers.list(all=True)
            return [
                {
                    "name": c.name,
                    "status": c.status,
                    "image": str(c.image.tags[0]) if c.image.tags else "unknown",
                }
                for c in containers
                if c.name.startswith(name_prefix)
            ]
        except Exception as exc:
            logger.error(f"[DockerHealer] list_containers failed: {exc}")
            return []

    # -----------------------------------------------------------------
    # Composite remediation by failure type
    # -----------------------------------------------------------------

    def remediate(self, failure_type: str, service_name: str) -> Dict:
        """
        Execute the appropriate Docker-level fix for a failure type.
        This is the main entry point called by the LangGraph remediation node.
        """
        container_name = f"synapse-{service_name}"

        action_map = {
            "service_crash": lambda: self.restart_container(container_name),
            "memory_leak": lambda: self.update_resources(
                container_name, mem_limit="2g"
            ),
            "disk_exhaustion": lambda: self.prune_system(),
            "network_degradation": lambda: self.fix_network(container_name),
            "high_cpu": lambda: self.restart_container(container_name),
            "connection_pool_exhaustion": lambda: self.restart_container(
                container_name
            ),
            "gc_pressure": lambda: self.restart_container(container_name),
        }

        action = action_map.get(failure_type)
        if action is None:
            return self._error_result(
                "remediate", container_name,
                f"No Docker action for failure_type '{failure_type}'"
            )

        logger.info(
            f"[DockerHealer] Executing Docker remediation for "
            f"{failure_type} on {container_name}"
        )
        return action()

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _error_result(action: str, container: str, error: str) -> Dict:
        logger.error(f"[DockerHealer] {action} failed for {container}: {error}")
        return {
            "action": action,
            "container": container,
            "status": "FAILED",
            "error": error,
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_healer: Optional[DockerHealer] = None


def get_docker_healer() -> DockerHealer:
    global _healer
    if _healer is None:
        _healer = DockerHealer()
    return _healer
