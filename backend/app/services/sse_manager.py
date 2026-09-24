"""
Synapse RiskOps - Server-Sent Events (SSE) Manager
===================================================
Owner: Person 2 | Week: 5

Manages real-time event streaming to the React dashboard.
Dispatches live notifications for:
- New incidents (incident_created)
- Status mutations & updates (incident_updated)
- Incident deletions (incident_deleted)
- High risk score alerts from ML engine (risk_alert)
- Keep-alive heartbeat (ping)
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional, Set
from fastapi import Request

logger = logging.getLogger("synapse.sse")


class SSEManager:
    """Pub/Sub manager for broadcasting real-time SSE messages to connected clients."""

    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()

    @property
    def active_connections(self) -> int:
        """Return the count of currently active SSE stream listeners."""
        return len(self._subscribers)

    async def subscribe(
        self,
        request: Optional[Request] = None,
        ping_interval: float = 15.0,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Subscribe a client connection to the real-time event stream.
        Yields events as they are broadcast.
        Automatically cleans up the queue when the client disconnects.
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.add(queue)
        logger.info(f"SSE client connected. Active listeners: {self.active_connections}")

        # Send initial connected handshake event
        yield {
            "event": "connected",
            "data": json.dumps({"status": "ready", "message": "Connected to Synapse RiskOps live stream"}),
        }

        try:
            while True:
                try:
                    # Wait for message with a timeout for keep-alive ping
                    message = await asyncio.wait_for(queue.get(), timeout=ping_interval)
                    yield message
                except asyncio.TimeoutError:
                    # Yield heartbeat keep-alive event
                    yield {
                        "event": "ping",
                        "data": "keep-alive",
                    }
        except (asyncio.CancelledError, GeneratorExit):
            pass
        finally:
            self._subscribers.discard(queue)
            logger.info(f"SSE client disconnected. Active listeners: {self.active_connections}")

    async def broadcast(self, event: str, data: Any):
        """Broadcast an event payload to all connected clients."""
        if not self._subscribers:
            return

        payload = {
            "event": event,
            "data": json.dumps(data, default=str),
        }

        dead_queues = set()
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning("Client queue full, dropping event for subscriber.")
            except Exception:
                dead_queues.add(queue)

        for q in dead_queues:
            self._subscribers.discard(q)

    async def broadcast_incident_created(self, incident: Any):
        """Helper to broadcast an incident creation event."""
        def _val(attr: str):
            if isinstance(incident, dict):
                return incident.get(attr)
            return getattr(incident, attr, None)

        inc_id = _val("id")
        service_id = _val("service_id")
        risk_score = _val("risk_score")
        confidence = _val("confidence")
        detected_at = _val("detected_at")

        data = {
            "id": str(inc_id) if inc_id is not None else None,
            "title": _val("title"),
            "severity": _val("severity"),
            "status": _val("status"),
            "service_id": str(service_id) if service_id is not None else None,
            "risk_score": float(risk_score) if risk_score is not None else None,
            "confidence": float(confidence) if confidence is not None else None,
            "detected_at": detected_at.isoformat() if hasattr(detected_at, "isoformat") else str(detected_at) if detected_at else None,
        }
        await self.broadcast("incident_created", data)

    async def broadcast_incident_updated(self, incident: Any):
        """Helper to broadcast an incident mutation event."""
        def _val(attr: str):
            if isinstance(incident, dict):
                return incident.get(attr)
            return getattr(incident, attr, None)

        inc_id = _val("id")
        resolved_at = _val("resolved_at")
        updated_at = _val("updated_at")

        data = {
            "id": str(inc_id) if inc_id is not None else None,
            "title": _val("title"),
            "severity": _val("severity"),
            "status": _val("status"),
            "resolved_at": resolved_at.isoformat() if hasattr(resolved_at, "isoformat") else str(resolved_at) if resolved_at else None,
            "updated_at": updated_at.isoformat() if hasattr(updated_at, "isoformat") else str(updated_at) if updated_at else None,
        }
        await self.broadcast("incident_updated", data)

    async def broadcast_incident_deleted(self, incident_id: Any):
        """Helper to broadcast an incident deletion event."""
        data = {
            "id": str(incident_id),
        }
        await self.broadcast("incident_deleted", data)

    async def broadcast_risk_alert(self, alert_data: Dict[str, Any]):
        """Helper to broadcast high-risk alert event from ML Engine."""
        await self.broadcast("risk_alert", alert_data)

    async def clear_all(self):
        """Discard all current subscribers."""
        self._subscribers.clear()


# Module-level singleton
sse_manager = SSEManager()
