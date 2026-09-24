"""
genai-agent/app/chatbot/router.py

FastAPI router for chatbot interaction endpoints:
- POST /message          - Receive user prompt, run LLM with tools, return response + card payloads
- GET  /health/{service} - Direct service health query endpoint
- GET  /history/{session_id} - Retrieve conversation history for active session
- DELETE /history/{session_id} - Reset conversation session
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.chatbot.engine import chatbot_engine
from app.chatbot.session_manager import session_manager
from app.chatbot.tools.ml_tools import get_service_risk_score, get_all_known_services


router = APIRouter(prefix="/api/chatbot", tags=["Chatbot"])


class ChatMessageRequest(BaseModel):
    message: str = Field(..., example="How is payment-service doing?")
    session_id: Optional[str] = Field(None, example="3fa85f64-5717-4562-b3fc-2c963f66afa6")


class ChatMessageResponse(BaseModel):
    response: str
    card: Optional[Dict[str, Any]] = None
    session_id: str
    service_name: Optional[str] = None


class SessionHistoryResponse(BaseModel):
    session_id: str
    messages: List[Dict[str, Any]]
    context: Dict[str, Any]


@router.post("/message", response_model=ChatMessageResponse)
async def chat_message(req: ChatMessageRequest):
    """
    Primary chatbot conversational endpoint.
    Processes user query in natural language, invokes SRE tools (e.g. Service Health Query),
    maintains multi-turn context memory, and returns formatted markdown text with UI card payloads.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    result = chatbot_engine.process_message(
        message=req.message, session_id=req.session_id
    )

    return ChatMessageResponse(
        response=result["response"],
        card=result.get("card"),
        session_id=result["session_id"],
        service_name=result.get("service_name"),
    )


@router.get("/health/{service_name}")
async def query_service_health(service_name: str):
    """
    Direct Service Health Query endpoint (Feature #1).
    Returns risk score, risk tier, failure prediction, horizon, and pre-formatted card payload.
    """
    data = get_service_risk_score(service_name)
    return data


@router.get("/services")
async def list_monitored_services():
    """
    Returns list of all services currently monitored by the Synapse RiskOps platform.
    """
    return {"services": get_all_known_services()}


@router.get("/history/{session_id}", response_model=SessionHistoryResponse)
async def get_history(session_id: str):
    """
    Retrieve message history and operational context for a given session ID.
    """
    messages = session_manager.get_messages(session_id)
    context = session_manager.get_context(session_id)
    return SessionHistoryResponse(
        session_id=session_id,
        messages=[m.model_dump() for m in messages],
        context=context.model_dump(),
    )


@router.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """
    Clear session memory to start a fresh conversation.
    """
    cleared = session_manager.clear_session(session_id)
    return {"session_id": session_id, "cleared": cleared}
