"""
genai-agent/tests/test_chatbot_tools.py

Unit tests for Chatbot Tool integrations (ML, Service Health Query).
Powers Feature #1: Service Health Query.
"""

from unittest.mock import patch, MagicMock
from app.chatbot.tools.ml_tools import (
    normalize_service_name,
    get_all_known_services,
    get_service_risk_score,
    get_service_metrics,
)


def test_normalize_service_name():
    assert normalize_service_name("payment-service") == "payment-service"
    assert normalize_service_name("PAYMENT") == "payment-service"
    assert normalize_service_name("payment service") == "payment-service"
    assert normalize_service_name("gateway") == "api-gateway"
    assert normalize_service_name("auth") == "auth-service"
    assert normalize_service_name("postgres") == "postgres-primary"
    assert normalize_service_name("db-primary") == "postgres-primary"
    assert normalize_service_name("redis") == "cache-layer"


def test_get_all_known_services():
    services = get_all_known_services()
    assert isinstance(services, list)
    assert "payment-service" in services
    assert "api-gateway" in services
    assert len(services) >= 10


def test_get_service_metrics():
    metrics = get_service_metrics("payment-service")
    assert metrics["service_name"] == "payment-service"
    assert "cpu_usage" in metrics
    assert "memory_usage" in metrics
    assert "error_rate" in metrics
    assert "response_time_p99" in metrics


def test_get_service_risk_score_fallback():
    # When ml-engine is unreachable, fallback heuristic is used
    with patch("requests.post", side_effect=Exception("Connection refused")):
        result = get_service_risk_score("payment-service")

    assert result["service_name"] == "payment-service"
    assert 0 <= result["risk_score"] <= 100
    assert result["risk_tier"] in ["HEALTHY", "WATCH", "CRITICAL"]
    assert "predicted_failure_type" in result
    assert "prediction_horizon_minutes" in result
    assert "status_summary" in result
    assert "card" in result
    assert result["card"]["type"] in ["risk_score", "risk_score_card"]
    assert result["card"]["data"]["service_name"] == "payment-service"


def test_get_service_risk_score_with_ml_engine():
    mock_ml_response = MagicMock()
    mock_ml_response.status_code = 200
    mock_ml_response.json.return_value = {
        "service_name": "order-service",
        "risk_score": 84.5,
        "risk_tier": "critical",
        "confidence": 0.92,
        "predicted_failure_type": "latency_degradation",
        "prediction_horizon_minutes": 35,
        "anomaly_detail": {
            "anomaly_score": 0.85,
            "is_anomaly": True,
            "top_contributing_features": ["response_time_p99"],
        },
        "forecast_detail": {
            "forecast_risk": 0.88,
            "predicted_failure_type": "latency_degradation",
            "prediction_horizon_minutes": 35,
            "trend_direction": "rising",
        },
    }

    with patch("requests.post", return_value=mock_ml_response):
        result = get_service_risk_score("order")

    assert result["service_name"] == "order-service"
    assert result["risk_score"] == 84.5
    assert result["risk_tier"] == "CRITICAL"
    assert result["predicted_failure_type"] == "latency_degradation"
    assert result["prediction_horizon_minutes"] == 35
    assert result["confidence"] == 0.92
    assert "CRITICAL RISK" in result["status_summary"]
