"""
genai-agent/app/chatbot/tools/__init__.py

Central registry exporting all tool definitions available to the Chatbot LLM.
"""

from typing import Dict, Any, Callable
from app.chatbot.tools.ml_tools import (
    get_service_risk_score,
    get_all_known_services,
    normalize_service_name,
)

# Registry of callable tools
CHATBOT_TOOLS: Dict[str, Callable[..., Any]] = {
    "get_service_risk_score": get_service_risk_score,
}


def get_all_chatbot_tools() -> Dict[str, Callable[..., Any]]:
    """Return all registered chatbot tools."""
    return CHATBOT_TOOLS


__all__ = [
    "get_service_risk_score",
    "get_all_known_services",
    "normalize_service_name",
    "get_all_chatbot_tools",
    "CHATBOT_TOOLS",
]
