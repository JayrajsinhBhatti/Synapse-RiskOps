"""
genai-agent/app/graph/chatbot_react_graph.py

LangGraph ReAct Node for conversational SRE operations alongside the RCA graph.
Powered by Gemini (ChatGoogleGenerativeAI) with tools for:
- Service Risk Score & Health
- Incidents List & Drilldown
- Stored Incident RCA & Gemini Explanation (incident_record.schema.json)
- Dependency Graph Traversal & Blast Radius
- RCA Diagnosis Pipeline Trigger
- Remediation Status Tracker & Runbooks
"""

import os
from typing import Dict, Any, Optional, List
from loguru import logger
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

load_dotenv()


# ===================================================================
# Tool Definitions for LangGraph ReAct Agent
# ===================================================================

@tool
def get_service_risk(service_name: str) -> str:
    """Query the current real-time risk score (0-100), risk tier (HEALTHY, WATCH, CRITICAL),
    and failure prediction for a microservice."""
    from app.chatbot.tools.ml_tools import get_service_risk_score
    res = get_service_risk_score(service_name)
    metrics = res.get("metrics", {})
    return (
        f"Service: {res['service_name']}\n"
        f"Risk Score: {res['risk_score']} ({res['risk_tier']})\n"
        f"Predicted Failure: {res.get('predicted_failure_type', 'None')} (horizon: {res.get('prediction_horizon_minutes', 0)} min)\n"
        f"CPU: {metrics.get('cpu_usage', 0)}%, Memory: {metrics.get('memory_usage', 0)}%, Error Rate: {metrics.get('error_rate', 0)}%\n"
        f"Summary: {res.get('status_summary', '')}"
    )


@tool
def list_system_incidents(status: Optional[str] = None, severity: Optional[str] = None) -> str:
    """List open, investigating, or resolved incidents from the backend with severity and assigned SREs."""
    from app.chatbot.tools.incident_tools import list_incidents
    res = list_incidents(status_filter=status, severity_filter=severity, limit=5)
    return res.get("text", "No incidents found.")


@tool
def get_incident_info(incident_id: str) -> str:
    """Retrieve full details of a specific incident by its ID (e.g. INC-4821)."""
    from app.chatbot.tools.incident_tools import get_incident_details
    res = get_incident_details(incident_id)
    return res.get("text", f"Incident {incident_id} not found.")


@tool
def explain_why_incident_happened(incident_id: str) -> str:
    """Explain why an incident happened by reading the stored root cause analysis,
    Gemini explanation, and failure propagation path from incident_record schema."""
    from app.chatbot.tools.incident_tools import explain_incident
    res = explain_incident(incident_id)
    return res.get("text", f"Could not explain incident {incident_id}.")


@tool
def get_topology_and_blast_radius(service_name: str) -> str:
    """Inspect upstream callers, downstream dependencies, and cascading blast radius
    if the specified service fails."""
    from app.chatbot.tools.topology_tools import get_service_dependencies
    res = get_service_dependencies(service_name)
    return res.get("text", f"No dependencies found for {service_name}.")


@tool
def trigger_rca_diagnosis(service_name: str) -> str:
    """Run an on-demand Root Cause Analysis (RCA) diagnosis on a service to identify
    anomalies and generate immediate SRE guidance."""
    from app.chatbot.tools.diagnosis_tools import trigger_diagnosis
    res = trigger_diagnosis(service_name)
    top_cause = res.get("root_cause_candidates", [{}])[0].get("cause", "unknown") if res.get("root_cause_candidates") else "unknown"
    return (
        f"Diagnosis complete for {res['service_name']}.\n"
        f"Risk Score: {res.get('risk_score', 0)} ({res.get('risk_tier', 'unknown')})\n"
        f"Top Root Cause: {top_cause}\n"
        f"Routing Decision: {res.get('routing_decision', 'escalate')}\n"
        f"Reason: {res.get('routing_reason', '')}"
    )


REACT_TOOLS = [
    get_service_risk,
    list_system_incidents,
    get_incident_info,
    explain_why_incident_happened,
    get_topology_and_blast_radius,
    trigger_rca_diagnosis,
]


SYSTEM_PROMPT = """You are the Synapse RiskOps Autonomous SRE Co-Pilot.
You assist Site Reliability Engineers in operating, diagnosing, and maintaining microservice clusters.

Your Capabilities:
- Check real-time risk scores and telemetry vitals (get_service_risk)
- Inspect active alerts and backend incidents (list_system_incidents, get_incident_info)
- Explain why specific incidents occurred using stored RCA and Gemini analyses (explain_why_incident_happened)
- Analyze upstream callers, downstream dependencies, and blast radius of failures (get_topology_and_blast_radius)
- Run on-demand root cause diagnosis on failing services (trigger_rca_diagnosis)

Guidelines:
1. Always be precise, technical, and concise like a senior staff SRE.
2. When answering about a service or incident, call the appropriate tool to retrieve real ground-truth data.
3. For dependency failures ("what breaks if X fails"), detail the cascading blast radius.
4. Format output with clean Markdown: bullet points, bold keywords, code blocks for service/incident names.
"""


class ChatbotReActAgent:
    """
    LangGraph ReAct agent executor for conversational SRE operations.
    """

    def __init__(self):
        self._agent = None
        self._init_agent()

    def _init_agent(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("[ChatbotReAct] GEMINI_API_KEY not found. Agent will use deterministic engine fallback.")
            return

        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langgraph.prebuilt import create_react_agent

            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash-lite",
                google_api_key=api_key,
                temperature=0.2,
                max_retries=0,
                timeout=6.0,
            )
            self._agent = create_react_agent(
                model=llm,
                tools=REACT_TOOLS,
                prompt=SYSTEM_PROMPT,
            )
            logger.info("[ChatbotReAct] LangGraph ReAct agent successfully initialized with Gemini.")
        except Exception as exc:
            logger.warning(f"[ChatbotReAct] Failed to initialize LangGraph ReAct agent: {exc}")
            self._agent = None

    def invoke(
        self,
        message: str,
        session_id: Optional[str] = None,
        service: Optional[str] = None,
        incident_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Invoke the ReAct agent with optional context awareness (service, incident_id).
        Falls back seamlessly to the deterministic engine when offline or no API key.
        """
        # If agent is not available, use the deterministic chatbot engine
        if self._agent is None:
            from app.chatbot.engine import chatbot_engine
            return chatbot_engine.process_message(
                message=message,
                session_id=session_id,
                service=service,
                incident_id=incident_id,
            )

        try:
            # Context augmentation
            context_prefix = ""
            if service:
                context_prefix += f"[Context: active service is `{service}`] "
            if incident_id:
                context_prefix += f"[Context: active incident is `{incident_id}`] "

            augmented_message = f"{context_prefix}{message}" if context_prefix else message

            messages = [HumanMessage(content=augmented_message)]
            result = self._agent.invoke({"messages": messages})

            # Extract final AI response
            final_message = result["messages"][-1]
            response_text = final_message.content

            # Look up card payload from deterministic engine context if available
            from app.chatbot.engine import chatbot_engine
            det_res = chatbot_engine.process_message(
                message=message,
                session_id=session_id,
                service=service,
                incident_id=incident_id,
            )

            return {
                "response": response_text,
                "card": det_res.get("card"),
                "session_id": session_id or det_res.get("session_id"),
                "service_name": service or det_res.get("service_name"),
                "intent": det_res.get("intent", "react_agent"),
            }

        except Exception as exc:
            logger.warning(f"[ChatbotReAct] ReAct agent execution failed ({exc}), falling back to deterministic engine.")
            from app.chatbot.engine import chatbot_engine
            return chatbot_engine.process_message(
                message=message,
                session_id=session_id,
                service=service,
                incident_id=incident_id,
            )


# Global singleton
chatbot_react_agent = ChatbotReActAgent()
