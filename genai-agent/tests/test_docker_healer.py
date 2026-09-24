"""
Tests for DockerHealer (Docker Python SDK integration).
Uses unittest.mock to mock DockerClient containers, networks, and images.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

AGENT_DIR = str(Path(__file__).resolve().parent.parent)
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

from app.remediation.docker_healer import DockerHealer
from docker.errors import NotFound, APIError


@pytest.fixture
def mock_healer():
    with patch("docker.from_env") as mock_from_env:
        mock_client = MagicMock()
        mock_from_env.return_value = mock_client
        healer = DockerHealer()
        healer.client = mock_client
        healer._connected = True
        return healer


def test_test_connection(mock_healer):
    mock_healer.client.ping.return_value = True
    assert mock_healer.test_connection() is True

    mock_healer.client.ping.side_effect = Exception("Daemon down")
    assert mock_healer.test_connection() is False


def test_restart_container_success(mock_healer):
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_healer.client.containers.get.return_value = mock_container

    result = mock_healer.restart_container("synapse-order-service")
    assert result["status"] == "SUCCESS"
    assert result["action"] == "restart"
    assert result["container"] == "synapse-order-service"
    mock_container.restart.assert_called_once()


def test_restart_container_not_found(mock_healer):
    mock_healer.client.containers.get.side_effect = NotFound("Container not found")

    result = mock_healer.restart_container("synapse-nonexistent")
    assert result["status"] == "FAILED"
    assert "not found" in result["error"].lower()


def test_update_resources(mock_healer):
    mock_container = MagicMock()
    mock_healer.client.containers.get.return_value = mock_container

    result = mock_healer.update_resources(
        "synapse-ml-engine",
        mem_limit="2g",
        cpu_quota=150000,
    )
    assert result["status"] == "SUCCESS"
    assert result["applied"]["mem_limit"] == "2g"
    mock_container.update.assert_called_once_with(
        mem_limit="2g", memswap_limit="2g", cpu_quota=150000
    )


def test_inspect_health(mock_healer):
    mock_container = MagicMock()
    mock_container.attrs = {
        "State": {
            "Status": "running",
            "Running": True,
            "ExitCode": 0,
            "Health": {"Status": "healthy", "FailingStreak": 0},
        },
        "RestartCount": 1,
    }
    mock_healer.client.containers.get.return_value = mock_container

    result = mock_healer.inspect_health("synapse-genai-agent")
    assert result["status"] == "SUCCESS"
    assert result["container_status"] == "running"
    assert result["health_status"] == "healthy"
    assert result["restart_count"] == 1


def test_fix_network(mock_healer):
    mock_network = MagicMock()
    mock_healer.client.networks.get.return_value = mock_network

    result = mock_healer.fix_network("synapse-backend", "synapse-riskops-network")
    assert result["status"] == "SUCCESS"
    mock_network.disconnect.assert_called_once()
    mock_network.connect.assert_called_once_with("synapse-backend")


def test_prune_system(mock_healer):
    mock_healer.client.containers.prune.return_value = {"SpaceReclaimed": 1048576}
    mock_healer.client.images.prune.return_value = {"SpaceReclaimed": 2097152}
    mock_healer.client.volumes.prune.return_value = {"SpaceReclaimed": 0}

    result = mock_healer.prune_system()
    assert result["status"] == "SUCCESS"
    assert result["space_reclaimed_bytes"] == 3145728
    assert result["space_reclaimed_mb"] == 3.0
