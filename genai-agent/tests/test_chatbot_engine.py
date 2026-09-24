"""
genai-agent/tests/test_chatbot_engine.py

Unit tests for Chatbot Engine, intent resolution, context memory, and router endpoints.
Powers Feature #1: Service Health Query & Feature #7: Conversation Memory.
"""

from fastapi.testclient import TestClient
from app.main import app
from app.chatbot.engine import ChatbotEngine
from app.chatbot.session_manager import session_manager


client = TestClient(app)


def test_service_health_query_payment_service():
    engine = ChatbotEngine()
    result = engine.process_message("How is payment-service doing?")

    assert result["service_name"] == "payment-service"
    assert "payment-service" in result["response"]
    assert result["card"] is not None
    assert result["card"]["type"] in ["risk_score", "risk_score_card"]
    assert result["card"]["data"]["service_name"] == "payment-service"
    assert "risk_score" in result["card"]["data"]
    assert "risk_tier" in result["card"]["data"]


def test_service_health_query_alias():
    engine = ChatbotEngine()
    result = engine.process_message("Check health of gateway")

    assert result["service_name"] == "api-gateway"
    assert result["card"] is not None
    assert result["card"]["data"]["service_name"] == "api-gateway"


def test_context_memory_follow_up():
    engine = ChatbotEngine()
    # Turn 1: query payment-service
    res1 = engine.process_message("How is payment-service doing?")
    session_id = res1["session_id"]
    assert res1["service_name"] == "payment-service"

    # Turn 2: follow-up referring to "it"
    res2 = engine.process_message("What is its risk score?", session_id=session_id)
    assert res2["service_name"] == "payment-service"
    assert res2["card"] is not None
    assert res2["card"]["data"]["service_name"] == "payment-service"


def test_greeting_intent():
    engine = ChatbotEngine()
    result = engine.process_message("Hello!")

    assert "Synapse RiskOps SRE Co-Pilot" in result["response"]
    assert result["card"] is None


def test_api_chatbot_message_endpoint():
    response = client.post(
        "/api/chatbot/message",
        json={"message": "How is order-service doing?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "order-service" in data["response"]
    assert data["service_name"] == "order-service"
    assert data["card"] is not None
    assert data["card"]["data"]["service_name"] == "order-service"
    assert "session_id" in data


def test_api_chatbot_health_direct_endpoint():
    response = client.get("/api/chatbot/health/auth-service")
    assert response.status_code == 200
    data = response.json()
    assert data["service_name"] == "auth-service"
    assert "risk_score" in data
    assert "risk_tier" in data
    assert "card" in data


def test_api_chatbot_history_and_clear():
    # Send a message
    res = client.post(
        "/api/chatbot/message",
        json={"message": "How is payment-service doing?"},
    )
    session_id = res.json()["session_id"]

    # Check history
    hist_res = client.get(f"/api/chatbot/history/{session_id}")
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert hist_data["session_id"] == session_id
    assert len(hist_data["messages"]) >= 2  # user + assistant

    # Clear history
    del_res = client.delete(f"/api/chatbot/history/{session_id}")
    assert del_res.status_code == 200
    assert del_res.json()["cleared"] is True
