"""
genai-agent/app/schemas/chatbot.py

Pydantic models for Chatbot API requests, responses, tool executions, and UI card payloads.
Aligns with shared/schemas/chatbot_message.schema.json.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime, timezone


class CardPayload(BaseModel):
    type: str = Field(..., description="Card type: risk_score, diagnosis_summary, etc.")
    data: Dict[str, Any] = Field(..., description="Payload data for rendering card")


class ChatMessageRequest(BaseModel):
    message: str = Field(..., example="How is payment-service doing?")
    session_id: Optional[str] = Field(None, example="3fa85f64-5717-4562-b3fc-2c963f66afa6")


class ChatMessageResponse(BaseModel):
    response: str
    card: Optional[CardPayload] = None
    cards: Optional[List[CardPayload]] = None
    session_id: str
    service_name: Optional[str] = None


class SessionHistoryResponse(BaseModel):
    session_id: str
    messages: List[Dict[str, Any]]
    context: Dict[str, Any]
