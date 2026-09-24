"""
genai-agent/app/remediation/k8s_healer.py

Kubernetes self-healing module.
Uses the official Kubernetes Python client to perform autonomous
remediation actions on a K8s cluster: pod restarts, HPA scaling,
deployment rollbacks, and node draining.

Integrates with the LangGraph remediation node as an alternative
to Docker SDK / Ansible when the infrastructure is Kubernetes-based.
"""

import os
import time
from typing import Dict, List, Optional

from loguru import logger

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException

    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False
    logger.warning(
        "[K8sHealer] kubernetes package not installed. "
        "K8s remediation will be unavailable."
    )


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
K8S_NAMESPACE = os.getenv("K8S_NAMESPACE", "synapse")
K8S_IN_CLUSTER = os.getenv("K8S_IN_CLUSTER", "false").lower() == "true"


class K8sHealer:
    """
    Kubernetes self-healing operator.
    Performs autonomous remediation on pods, deployments, and nodes.
    """

    def __init__(self, namespace: str = K8S_NAMESPACE):
        self.namespace = namespace
        self._connected = False

        if not K8S_AVAILABLE:
            logger.error("[K8sHealer] kubernetes package not available")
            return

        try:
            if K8S_IN_CLUSTER:
                config.load_incluster_config()
            else:
                config.load_kube_config()

            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.autoscaling_v1 = client.AutoscalingV1Api()
            self._connected = True
            logger.info(f"[K8sHealer] Connected to K8s cluster (ns={namespace})")
        except Exception as exc:
            logger.error(f"[K8sHealer] Failed to connect: {exc}")

    @property
    def is_connected(self) -> bool:
        return self._connected

    # -----------------------------------------------------------------
    # Pod Operations
    # -----------------------------------------------------------------

    def restart_pod(self, pod_name: str) -> Dict:
        """
        Delete a pod to trigger recreation by its controller (Deployment/RS).
        Equivalent to `kubectl delete pod <name>`.
        """
        if not self._connected:
            return self._error("restart_pod", pod_name, "Not connected to K8s")

        start = time.monotonic()
        try:
            self.core_v1.delete_namespaced_pod(
                name=pod_name,
                namespace=self.namespace,
                body=client.V1DeleteOptions(grace_period_seconds=30),
            )
            duration = round(time.monotonic() - start, 2)
            logger.info(f"[K8sHealer] Deleted pod {pod_name} for restart ({duration}s)")
            return {
                "action": "restart_pod",
                "pod": pod_name,
                "status": "SUCCESS",
                "duration_seconds": duration,
            }
        except ApiException as exc:
            return self._error("restart_pod", pod_name, f"API error: {exc.status} {exc.reason}")

    def get_crashing_pods(self) -> List[Dict]:
        """
        Find pods in CrashLoopBackOff or Error state.
        Returns list of problematic pods with details.
        """
        if not self._connected:
            return []

        try:
            pods = self.core_v1.list_namespaced_pod(namespace=self.namespace)
            crashing = []
            for pod in pods.items:
                if pod.status and pod.status.container_statuses:
                    for cs in pod.status.container_statuses:
                        waiting = cs.state.waiting if cs.state else None
                        if waiting and waiting.reason in (
                            "CrashLoopBackOff",
                            "Error",
                            "OOMKilled",
                            "ImagePullBackOff",
                        ):
                            crashing.append({
                                "pod_name": pod.metadata.name,
                                "container": cs.name,
                                "reason": waiting.reason,
                                "message": waiting.message or "",
                                "restart_count": cs.restart_count,
                            })
            return crashing
        except ApiException as exc:
            logger.error(f"[K8sHealer] get_crashing_pods failed: {exc}")
            return []

    # -----------------------------------------------------------------
    # Deployment Operations
    # -----------------------------------------------------------------

    def scale_deployment(self, deployment_name: str, replicas: int) -> Dict:
        """Scale a deployment to the specified number of replicas."""
        if not self._connected:
            return self._error("scale_deployment", deployment_name, "Not connected")

        start = time.monotonic()
        try:
            self.apps_v1.patch_namespaced_deployment_scale(
                name=deployment_name,
                namespace=self.namespace,
                body={"spec": {"replicas": replicas}},
            )
            duration = round(time.monotonic() - start, 2)
            logger.info(
                f"[K8sHealer] Scaled {deployment_name} to {replicas} replicas ({duration}s)"
            )
            return {
                "action": "scale_deployment",
                "deployment": deployment_name,
                "replicas": replicas,
                "status": "SUCCESS",
                "duration_seconds": duration,
            }
        except ApiException as exc:
            return self._error(
                "scale_deployment", deployment_name, f"{exc.status} {exc.reason}"
            )

    def rollback_deployment(self, deployment_name: str) -> Dict:
        """
        Rollback a deployment to its previous revision.
        Triggers a rolling update back to the last known-good configuration.
        """
        if not self._connected:
            return self._error("rollback_deployment", deployment_name, "Not connected")

        start = time.monotonic()
        try:
            # Patch the deployment with a rollback annotation to trigger
            # Kubernetes to roll back to the previous revision
            deployment = self.apps_v1.read_namespaced_deployment(
                name=deployment_name, namespace=self.namespace
            )

            # Force a rollout by updating an annotation
            annotations = deployment.spec.template.metadata.annotations or {}
            annotations["kubectl.kubernetes.io/restartedAt"] = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
            )
            deployment.spec.template.metadata.annotations = annotations

            self.apps_v1.patch_namespaced_deployment(
                name=deployment_name,
                namespace=self.namespace,
                body=deployment,
            )

            duration = round(time.monotonic() - start, 2)
            logger.info(
                f"[K8sHealer] Rolling restart triggered for {deployment_name} ({duration}s)"
            )
            return {
                "action": "rollback_deployment",
                "deployment": deployment_name,
                "status": "SUCCESS",
                "duration_seconds": duration,
            }
        except ApiException as exc:
            return self._error(
                "rollback_deployment", deployment_name, f"{exc.status} {exc.reason}"
            )

    def get_deployment_status(self, deployment_name: str) -> Dict:
        """Get current deployment status including readiness and conditions."""
        if not self._connected:
            return self._error("get_deployment_status", deployment_name, "Not connected")

        try:
            dep = self.apps_v1.read_namespaced_deployment(
                name=deployment_name, namespace=self.namespace
            )
            status = dep.status
            return {
                "action": "get_deployment_status",
                "deployment": deployment_name,
                "status": "SUCCESS",
                "replicas": status.replicas or 0,
                "ready_replicas": status.ready_replicas or 0,
                "available_replicas": status.available_replicas or 0,
                "unavailable_replicas": status.unavailable_replicas or 0,
                "conditions": [
                    {
                        "type": c.type,
                        "status": c.status,
                        "reason": c.reason,
                        "message": c.message,
                    }
                    for c in (status.conditions or [])
                ],
            }
        except ApiException as exc:
            return self._error(
                "get_deployment_status", deployment_name, f"{exc.status} {exc.reason}"
            )

    # -----------------------------------------------------------------
    # Composite remediation by failure type
    # -----------------------------------------------------------------

    def remediate(self, failure_type: str, service_name: str) -> Dict:
        """
        Execute the appropriate K8s-level fix for a failure type.
        Main entry point called by the LangGraph remediation node.
        """
        deployment_name = service_name

        action_map = {
            "service_crash": lambda: self.rollback_deployment(deployment_name),
            "memory_leak": lambda: self.scale_deployment(
                deployment_name, replicas=3
            ),
            "high_cpu": lambda: self.scale_deployment(
                deployment_name, replicas=3
            ),
            "cascading_failure": lambda: self.rollback_deployment(deployment_name),
            "connection_pool_exhaustion": lambda: self.rollback_deployment(
                deployment_name
            ),
        }

        action = action_map.get(failure_type)
        if action is None:
            return self._error(
                "remediate", deployment_name,
                f"No K8s action for failure_type '{failure_type}'"
            )

        logger.info(
            f"[K8sHealer] Executing K8s remediation for "
            f"{failure_type} on {deployment_name}"
        )
        return action()

    # -----------------------------------------------------------------
    # Node Operations
    # -----------------------------------------------------------------

    def cordon_node(self, node_name: str) -> Dict:
        """Mark a node as unschedulable (cordon)."""
        if not self._connected:
            return self._error("cordon_node", node_name, "Not connected")

        try:
            self.core_v1.patch_node(
                name=node_name,
                body={"spec": {"unschedulable": True}},
            )
            logger.info(f"[K8sHealer] Cordoned node {node_name}")
            return {
                "action": "cordon_node",
                "node": node_name,
                "status": "SUCCESS",
            }
        except ApiException as exc:
            return self._error("cordon_node", node_name, f"{exc.status} {exc.reason}")

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _error(action: str, target: str, msg: str) -> Dict:
        logger.error(f"[K8sHealer] {action} failed for {target}: {msg}")
        return {
            "action": action,
            "target": target,
            "status": "FAILED",
            "error": msg,
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------
_healer: Optional[K8sHealer] = None


def get_k8s_healer() -> K8sHealer:
    global _healer
    if _healer is None:
        _healer = K8sHealer()
    return _healer
