"""
Synapse RiskOps - Gmail SMTP Email Service Tests
================================================
Validates Gmail SMTP email alerting functionality, template rendering,
error handling, and orchestrator lifecycle integration.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.services.email_service import EmailService, email_service
from app.services.orchestrator import OrchestrationService


def test_email_service_configuration_defaults():
    """Verify default credentials and host configuration."""
    service = EmailService()
    assert service.smtp_host == "smtp.gmail.com"
    assert service.smtp_port == 587
    assert service.sender_email == "spareid9687@gmail.com"
    assert service.admin_email == "jayrajsinhbhatti9687@gmail.com"
    assert service.use_tls is True
    assert service.enabled is True


def test_incident_email_template_rendering():
    """Verify HTML and plain-text templates include all critical incident details."""
    service = EmailService()
    test_data = {
        "service_name": "order-service",
        "incident_id": "INC-TEST-12345",
        "severity": "CRITICAL",
        "risk_score": 92.4,
        "failure_type": "latency_degradation",
        "root_cause": "payment-service",
        "ml_confidence": 0.95,
        "rca_confidence": 0.88,
        "guidance": "High queuing detected on payment-service downstream pool.",
        "routing_decision": "human_approval",
        "metrics": {"response_time_p99": 350.2, "error_rate": 8.5},
    }

    html = service._build_incident_html(test_data)
    text = service._build_incident_text(test_data)

    # Assert critical markers in HTML
    assert "order-service" in html
    assert "CRITICAL" in html
    assert "92.4%" in html
    assert "payment-service" in html
    assert "INC-TEST-12345" in html
    assert "spareid9687@gmail.com" in html
    assert "jayrajsinhbhatti9687@gmail.com" in html
    assert "http://localhost:5173/dashboard?incident_id=INC-TEST-12345" in html
    assert "350.2" in html

    # Assert critical markers in plain text
    assert "SERVICE PREDICTED TO FAIL: order-service" in text
    assert "Severity: CRITICAL" in text
    assert "Risk Score: 92.4%" in text
    assert "Root Cause Service: payment-service" in text
    assert "http://localhost:5173/dashboard?incident_id=INC-TEST-12345" in text


@pytest.mark.asyncio
async def test_email_dispatch_skipped_when_no_credentials():
    """Verify graceful handling without throwing when SMTP password is not set."""
    service = EmailService(sender_password="")
    res = await service.send_incident_alert({
        "service_name": "inventory-service",
        "incident_id": "INC-NO-CRED",
        "risk_score": 85.0,
        "severity": "HIGH",
    })

    assert res["success"] is False
    assert res["status"] == "NO_CREDENTIALS"
    assert "SMTP_PASSWORD" in res["detail"]


@pytest.mark.asyncio
async def test_email_dispatch_success_with_mocked_smtp():
    """Verify successful Gmail SMTP connection, STARTTLS handshake, authentication and delivery."""
    service = EmailService(
        sender_email="spareid9687@gmail.com",
        sender_password="abcd-efgh-ijkl-mnop",
        admin_email="jayrajsinhbhatti9687@gmail.com",
    )

    mock_smtp_instance = MagicMock()
    with patch("smtplib.SMTP", return_value=mock_smtp_instance):
        res = await service.send_incident_alert({
            "service_name": "auth-service",
            "incident_id": "INC-MOCK-OK",
            "risk_score": 90.5,
            "severity": "CRITICAL",
            "failure_type": "cpu_saturation",
        })

        assert res["success"] is True
        assert res["status"] == "SENT"
        assert res["recipient"] == "jayrajsinhbhatti9687@gmail.com"
        assert res["sender"] == "spareid9687@gmail.com"

        # Verify SMTP interaction sequence
        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with("spareid9687@gmail.com", "abcd-efgh-ijkl-mnop")
        mock_smtp_instance.sendmail.assert_called_once()
        mock_smtp_instance.quit.assert_called_once()


@pytest.mark.asyncio
async def test_email_dispatch_auth_failure_handling():
    """Verify informative error handling when Gmail authentication fails."""
    import smtplib

    service = EmailService(
        sender_email="spareid9687@gmail.com",
        sender_password="invalid_password",
        admin_email="jayrajsinhbhatti9687@gmail.com",
    )

    mock_smtp_instance = MagicMock()
    mock_smtp_instance.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Authentication failed")

    with patch("smtplib.SMTP", return_value=mock_smtp_instance):
        res = await service.send_incident_alert({
            "service_name": "auth-service",
            "incident_id": "INC-MOCK-AUTH-FAIL",
            "risk_score": 95.0,
            "severity": "CRITICAL",
        })

        assert res["success"] is False
        assert res["status"] == "AUTH_FAILED"
        assert "Google requires a 16-character App Password" in res["detail"]


@pytest.mark.asyncio
async def test_orchestrator_triggers_gmail_alert():
    """Verify that orchestrator.orchestrate_incident_lifecycle triggers Gmail SMTP alert."""
    orch = OrchestrationService()
    orch._call_ml_engine_analyze = AsyncMock(return_value={
        "service_name": "payment-service",
        "prediction": {
            "risk_score": 88.0,
            "confidence": 0.92,
            "predicted_failure_type": "database_connection_exhaustion",
            "risk_threshold": 75.0,
        },
        "diagnosis": {
            "rca_candidates": [{"service": "payment-service", "label": "ROOT_CAUSE", "confidence": 0.90}],
            "propagation_path": ["payment-service"],
            "rca_confidence": 0.88,
            "gemini_explanation": "DB connection pool depleted.",
        },
    })
    orch._call_genai_diagnose = AsyncMock(return_value=None)
    orch._send_n8n_incident = AsyncMock(return_value=True)
    orch._send_incident_email = AsyncMock(return_value={"success": True, "status": "SENT"})

    record = await orch.orchestrate_incident_lifecycle(
        service_name="payment-service",
        metrics={"active_connections": 100.0, "error_rate": 6.2},
        db=None,
    )

    assert record.prediction["risk_score"] == 88.0
    orch._send_incident_email.assert_called_once()
    call_payload = orch._send_incident_email.call_args[0][0]
    assert call_payload["service_name"] == "payment-service"
    assert call_payload["severity"] == "CRITICAL"
    assert call_payload["failure_type"] == "database_connection_exhaustion"
    assert call_payload["risk_score"] == 88.0
