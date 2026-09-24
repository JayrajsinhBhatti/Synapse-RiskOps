"""
genai-agent/app/chatbot/engine.py

Chatbot execution engine.
- Parses user intent from natural language prompts
- Coordinates SRE tool calling (Feature #1: get_service_risk_score)
- Manages conversational session memory and context resolution
- Emits structured text and card payloads for the UI
"""

import os
import re
from typing import Optional, Dict, Any, Tuple
from loguru import logger

from app.chatbot.session_manager import session_manager, SessionState
from app.chatbot.tools.ml_tools import (
    get_service_risk_score,
    normalize_service_name,
    get_all_known_services,
)
from app.chatbot.prompts import SYSTEM_PROMPT, SERVICE_HEALTH_RESPONSE_TEMPLATE


class ChatbotEngine:
    """
    Core engine powering conversational SRE interactions in Synapse RiskOps.
    """

    def __init__(self):
        self.known_services = get_all_known_services()

    def _extract_service_from_text(
        self, text: str, current_service: Optional[str] = None
    ) -> Tuple[Optional[str], bool]:
        """
        Extract target service name from user prompt.
        Returns (service_name, is_follow_up).
        """
        lower = text.lower().strip()

        # Check for context follow-ups e.g. "how is it doing", "what is its risk score"
        context_pronouns = ["it", "this service", "the service", "its"]
        for pronoun in context_pronouns:
            pattern = rf"\b{pronoun}\b"
            if re.search(pattern, lower) and current_service:
                return current_service, True

        # Check explicit service names
        words = re.findall(r"[\w-]+", lower)
        for word in words:
            normalized = normalize_service_name(word)
            if normalized:
                return normalized, False

        # Check combined 2-word tokens (e.g. "payment service", "api gateway")
        for i in range(len(words) - 1):
            two_words = f"{words[i]}-{words[i+1]}"
            normalized = normalize_service_name(two_words)
            if normalized:
                return normalized, False

        return None, False

    def _is_service_health_query(self, text: str, detected_service: Optional[str]) -> bool:
        """
        Determine if the user query is asking about the health/risk of a service.
        """
        lower = text.lower().strip()
        health_keywords = [
            "health",
            "doing",
            "risk",
            "score",
            "status",
            "vitals",
            "condition",
            "how is",
            "how's",
            "check",
            "state",
            "metrics",
            "anomal",
        ]
        has_health_keyword = any(kw in lower for kw in health_keywords)

        if detected_service and has_health_keyword:
            return True

        # Catch specific phrasing like "How is payment-service doing?"
        if re.search(r"how\s+is\s+[\w-]+\s+doing", lower):
            return True

        if re.search(r"[\w-]+\s+health", lower):
            return True

        return False

    def process_message(
        self, message: str, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an incoming chat message and return response text + card payload.
        """
        session: SessionState = session_manager.get_or_create_session(session_id)
        session_id = session.session_id

        # 1. Record incoming user message
        session_manager.add_message(session_id=session_id, role="user", content=message)

        current_service = session.context.current_service
        target_service, is_follow_up = self._extract_service_from_text(
            message, current_service=current_service
        )

        # 2. Check for Feature #1: Service Health Query
        if self._is_service_health_query(message, target_service):
            if not target_service:
                available_services_str = ", ".join(f"`{s}`" for s in self.known_services[:6])
                response_text = (
                    "Which service would you like to check? You can ask about services like: "
                    f"{available_services_str}."
                )
                session_manager.add_message(
                    session_id=session_id, role="assistant", content=response_text
                )
                return {
                    "response": response_text,
                    "card": None,
                    "session_id": session_id,
                    "service_name": None,
                }

            # Update session context memory (Feature #7)
            session_manager.update_context(session_id, current_service=target_service)

            # Call Tool: get_service_risk_score (Feature #1)
            logger.info(f"Chatbot executing get_service_risk_score for service={target_service}")
            risk_data = get_service_risk_score(target_service)

            horizon = (
                f"{risk_data['prediction_horizon_minutes']} minutes"
                if risk_data["prediction_horizon_minutes"] > 0
                else "No imminent failure"
            )

            metrics = risk_data.get("metrics", {})
            response_text = SERVICE_HEALTH_RESPONSE_TEMPLATE.format(
                service_name=target_service,
                risk_score=risk_data["risk_score"],
                risk_tier=risk_data["risk_tier"],
                predicted_failure_type=risk_data["predicted_failure_type"],
                prediction_horizon=horizon,
                confidence=int(risk_data["confidence"] * 100),
                cpu_usage=metrics.get("cpu_usage", 0.0),
                memory_usage=metrics.get("memory_usage", 0.0),
                error_rate=metrics.get("error_rate", 0.0),
                p99_latency=metrics.get("response_time_p99", 0.0),
                summary=risk_data["status_summary"],
            )

            card_payload = risk_data.get("card")

            session_manager.add_message(
                session_id=session_id,
                role="assistant",
                content=response_text,
                card=card_payload,
            )

            return {
                "response": response_text,
                "card": card_payload,
                "session_id": session_id,
                "service_name": target_service,
                "risk_data": risk_data,
            }

        # 3. Check for Help / Capabilities / Greetings
        lower_msg = message.lower().strip()
        if any(greet in lower_msg for greet in ["hi", "hello", "hey", "help", "capabilities"]):
            response_text = (
                "👋 Hello! I am your **Synapse RiskOps SRE Co-Pilot**.\n\n"
                "I monitor your microservice mesh in real-time. Here are a few things you can ask me:\n"
                "- *\"How is payment-service doing?\"* (Service Health & Risk Score)\n"
                "- *\"Check health of api-gateway\"*\n"
                "- *\"What is the risk score of auth-service?\"*\n"
                "- *\"Show status of postgres-primary\"*\n\n"
                f"Currently monitoring **{len(self.known_services)} microservices** across the cluster."
            )
            session_manager.add_message(
                session_id=session_id, role="assistant", content=response_text
            )
            return {
                "response": response_text,
                "card": None,
                "session_id": session_id,
                "service_name": current_service,
            }

        # 4. Fallback response for unhandled prompts
        response_text = (
            f"I didn't quite catch that. You can ask me about any service's operational health, such as: "
            f"*\"How is {current_service or 'payment-service'} doing?\"* or *\"Check risk score of auth-service\"*."
        )
        session_manager.add_message(
            session_id=session_id, role="assistant", content=response_text
        )
        return {
            "response": response_text,
            "card": None,
            "session_id": session_id,
            "service_name": current_service,
        }


# Global singleton chatbot engine
chatbot_engine = ChatbotEngine()
