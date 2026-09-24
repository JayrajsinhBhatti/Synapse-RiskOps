"""
genai-agent/app/chatbot/session_manager.py

Session & state manager for chatbot interactions (Feature #7: Conversation Memory).
- Tracks conversation message history per session ID
- Maintains active operational context (current service_name, incident_id in focus)
- Manages pending actions waiting for human confirmation
"""

import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str  # "user", "assistant", "system"
    content: str
    card: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SessionContext(BaseModel):
    current_service: Optional[str] = None
    current_incident_id: Optional[str] = None
    pending_action: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionState(BaseModel):
    session_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    messages: List[ChatMessage] = Field(default_factory=list)
    context: SessionContext = Field(default_factory=SessionContext)


class SessionManager:
    """
    In-memory, thread-safe session manager for multi-turn chatbot conversations.
    """

    def __init__(self):
        self._sessions: Dict[str, SessionState] = {}
        self._lock = threading.Lock()

    def get_or_create_session(self, session_id: Optional[str] = None) -> SessionState:
        with self._lock:
            if not session_id:
                session_id = str(uuid.uuid4())
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionState(session_id=session_id)
            return self._sessions[session_id]

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        card: Optional[Dict[str, Any]] = None,
    ) -> ChatMessage:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionState(session_id=session_id)

            msg = ChatMessage(role=role, content=content, card=card)
            session = self._sessions[session_id]
            session.messages.append(msg)
            session.updated_at = datetime.now(timezone.utc).isoformat()
            return msg

    def get_messages(self, session_id: str) -> List[ChatMessage]:
        with self._lock:
            session = self._sessions.get(session_id)
            return list(session.messages) if session else []

    def get_context(self, session_id: str) -> SessionContext:
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return SessionContext()
            return session.context

    def update_context(self, session_id: str, **kwargs) -> SessionContext:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionState(session_id=session_id)
            session = self._sessions[session_id]
            session.updated_at = datetime.now(timezone.utc).isoformat()
            for key, val in kwargs.items():
                if hasattr(session.context, key):
                    setattr(session.context, key, val)
                else:
                    session.context.metadata[key] = val
            return session.context

    def clear_session(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False


# Global singleton instance
session_manager = SessionManager()
