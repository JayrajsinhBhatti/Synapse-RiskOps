"""
Tests for AnsibleExecutor (Semaphore API integration).
Uses unittest.mock for zero-dependency HTTP client mocking.
"""

import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import pytest

# Ensure genai-agent is in sys.path
AGENT_DIR = str(Path(__file__).resolve().parent.parent)
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

from app.remediation.ansible_executor import (
    AnsibleExecutor,
    FAILURE_TO_PLAYBOOK,
    PlaybookTemplate,
)


@pytest.fixture
def executor():
    return AnsibleExecutor(
        base_url="http://mock-semaphore:3000",
        api_token="test-token",
        project_id=1,
    )


def test_failure_type_mapping():
    assert FAILURE_TO_PLAYBOOK["service_crash"] == PlaybookTemplate.RESTART_SERVICE
    assert FAILURE_TO_PLAYBOOK["memory_leak"] == PlaybookTemplate.SCALE_RESOURCES
    assert FAILURE_TO_PLAYBOOK["disk_exhaustion"] == PlaybookTemplate.CLEAR_DISK
    assert FAILURE_TO_PLAYBOOK["network_degradation"] == PlaybookTemplate.RESET_NETWORK
    assert FAILURE_TO_PLAYBOOK["high_cpu"] == PlaybookTemplate.SCALE_RESOURCES


import asyncio

def test_execute_remediation_unmapped_failure(executor):
    result = asyncio.run(
        executor.execute_remediation(
            failure_type="unknown_alien_failure",
            service_name="payment-service",
            incident_id="INC-123",
            risk_score=90.0,
        )
    )
    assert result["status"] == "SKIPPED"
    assert result["task_id"] is None


def test_execute_remediation_success(executor):
    post_resp = MagicMock()
    post_resp.status_code = 201
    post_resp.json.return_value = {"id": 42}
    post_resp.raise_for_status = MagicMock()

    get_resp = MagicMock()
    get_resp.status_code = 200
    get_resp.json.return_value = {"status": "success"}

    mock_client = AsyncMock()
    mock_client.post.return_value = post_resp
    mock_client.get.return_value = get_resp
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(
            executor.execute_remediation(
                failure_type="service_crash",
                service_name="order-service",
                incident_id="INC-001",
                risk_score=88.5,
            )
        )

        assert result["status"] == "SUCCESS"
        assert result["task_id"] == 42
        assert result["duration"] >= 0


def test_execute_remediation_failure(executor):
    post_resp = MagicMock()
    post_resp.status_code = 201
    post_resp.json.return_value = {"id": 99}
    post_resp.raise_for_status = MagicMock()

    get_resp = MagicMock()
    get_resp.status_code = 200
    get_resp.json.return_value = {"status": "error"}

    mock_client = AsyncMock()
    mock_client.post.return_value = post_resp
    mock_client.get.return_value = get_resp
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = asyncio.run(
            executor.execute_remediation(
                failure_type="disk_exhaustion",
                service_name="auth-service",
                incident_id="INC-002",
                risk_score=95.0,
            )
        )

        assert result["status"] == "FAILED"
        assert result["task_id"] == 99
