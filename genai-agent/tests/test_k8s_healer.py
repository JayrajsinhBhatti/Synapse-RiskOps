"""
Tests for K8sHealer (Kubernetes self-healing operator).
Uses unittest.mock to mock CoreV1Api and AppsV1Api.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

AGENT_DIR = str(Path(__file__).resolve().parent.parent)
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

from app.remediation.k8s_healer import K8sHealer


@pytest.fixture
def mock_k8s():
    with patch("kubernetes.config.load_kube_config"), \
         patch("kubernetes.client.CoreV1Api") as mock_core, \
         patch("kubernetes.client.AppsV1Api") as mock_apps, \
         patch("kubernetes.client.AutoscalingV1Api") as mock_auto:

        healer = K8sHealer(namespace="synapse")
        healer.core_v1 = mock_core.return_value
        healer.apps_v1 = mock_apps.return_value
        healer.autoscaling_v1 = mock_auto.return_value
        healer._connected = True
        return healer


def test_restart_pod(mock_k8s):
    result = mock_k8s.restart_pod("synapse-order-service-789")
    assert result["status"] == "SUCCESS"
    assert result["action"] == "restart_pod"
    mock_k8s.core_v1.delete_namespaced_pod.assert_called_once()


def test_scale_deployment(mock_k8s):
    result = mock_k8s.scale_deployment("synapse-ml-engine", replicas=3)
    assert result["status"] == "SUCCESS"
    assert result["replicas"] == 3
    mock_k8s.apps_v1.patch_namespaced_deployment_scale.assert_called_once_with(
        name="synapse-ml-engine",
        namespace="synapse",
        body={"spec": {"replicas": 3}},
    )


def test_get_crashing_pods(mock_k8s):
    # Mock pod in CrashLoopBackOff
    mock_pod = MagicMock()
    mock_pod.metadata.name = "synapse-genai-agent-xyz"
    mock_cs = MagicMock()
    mock_cs.name = "genai-agent"
    mock_cs.restart_count = 5
    mock_cs.state.waiting.reason = "CrashLoopBackOff"
    mock_cs.state.waiting.message = "Back-off restarting failed container"
    mock_pod.status.container_statuses = [mock_cs]

    mock_pods_list = MagicMock()
    mock_pods_list.items = [mock_pod]
    mock_k8s.core_v1.list_namespaced_pod.return_value = mock_pods_list

    crashing = mock_k8s.get_crashing_pods()
    assert len(crashing) == 1
    assert crashing[0]["pod_name"] == "synapse-genai-agent-xyz"
    assert crashing[0]["reason"] == "CrashLoopBackOff"


def test_rollback_deployment(mock_k8s):
    mock_deployment = MagicMock()
    mock_deployment.spec.template.metadata.annotations = {}
    mock_k8s.apps_v1.read_namespaced_deployment.return_value = mock_deployment

    result = mock_k8s.rollback_deployment("synapse-backend")
    assert result["status"] == "SUCCESS"
    mock_k8s.apps_v1.patch_namespaced_deployment.assert_called_once()
