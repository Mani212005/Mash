"""
Mash Voice - WebSocket Routes

Real-time WebSocket endpoints for live call updates.
"""

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.core.state import get_state_manager
from app.utils import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages WebSocket connections for live updates."""

    def __init__(self):
        # call_id -> list of WebSocket connections
        self._connections: dict[str, list[WebSocket]] = {}
        # For broadcast to all dashboards
        self._dashboard_connections: list[WebSocket] = []

    async def connect_call(self, call_id: str, websocket: WebSocket):
        """Connect a WebSocket to a specific call."""
        await websocket.accept()
        if call_id not in self._connections:
            self._connections[call_id] = []
        self._connections[call_id].append(websocket)
        logger.info("WebSocket connected to call", call_id=call_id)

    async def connect_dashboard(self, websocket: WebSocket):
        """Connect a WebSocket for dashboard updates."""
        await websocket.accept()
        self._dashboard_connections.append(websocket)
        logger.info("Dashboard WebSocket connected")

    def disconnect_call(self, call_id: str, websocket: WebSocket):
        """Disconnect a WebSocket from a call."""
        if call_id in self._connections:
            self._connections[call_id].remove(websocket)
            if not self._connections[call_id]:
                del self._connections[call_id]
        logger.info("WebSocket disconnected from call", call_id=call_id)

    def disconnect_dashboard(self, websocket: WebSocket):
        """Disconnect a dashboard WebSocket."""
        if websocket in self._dashboard_connections:
            self._dashboard_connections.remove(websocket)
        logger.info("Dashboard WebSocket disconnected")

    async def send_to_call(self, call_id: str, message: dict[str, Any]):
        """Send a message to all connections watching a call."""
        if call_id in self._connections:
            message_str = json.dumps(message)
            for connection in self._connections[call_id]:
                try:
                    await connection.send_text(message_str)
                except Exception as e:
                    logger.warning(
                        "Failed to send to WebSocket",
                        call_id=call_id,
                        error=str(e),
                    )

    async def broadcast_to_dashboards(self, message: dict[str, Any]):
        """Broadcast a message to all dashboard connections."""
        message_str = json.dumps(message)
        for connection in self._dashboard_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.warning("Failed to broadcast to dashboard", error=str(e))


# Singleton connection manager
_connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    return _connection_manager


@router.websocket("/calls/{call_id}/live")
async def call_live_stream(websocket: WebSocket, call_id: str):
    """
    WebSocket endpoint for live call updates.
    
    Sends real-time events:
    - transcript: ASR transcripts
    - agent_response: Agent responses
    - event: Call events (transfers, tool calls, etc.)
    """
    manager = get_connection_manager()
    await manager.connect_call(call_id, websocket)
    
    try:
        while True:
            # Keep connection alive and handle any incoming messages
            data = await websocket.receive_text()
            
            # Handle ping/pong for keepalive
            if data == "ping":
                await websocket.send_text("pong")
            
    except WebSocketDisconnect:
        manager.disconnect_call(call_id, websocket)
    except Exception as e:
        logger.exception("Live stream error", call_id=call_id, error=str(e))
        manager.disconnect_call(call_id, websocket)


@router.websocket("/dashboard/live")
async def dashboard_live_stream(websocket: WebSocket):
    """
    WebSocket endpoint for dashboard updates.
    
    Sends real-time events:
    - call_started: New call initiated
    - call_ended: Call completed
    - call_updated: Call status change
    - system_status: System health updates
    """
    manager = get_connection_manager()
    await manager.connect_dashboard(websocket)
    
    try:
        # Send initial state
        state_manager = get_state_manager()
        active_calls = await state_manager.get_active_calls()
        
        await websocket.send_text(json.dumps({
            "type": "initial_state",
            "data": {
                "active_calls": list(active_calls),
            },
        }))
        
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            
            if data == "ping":
                await websocket.send_text("pong")
            
    except WebSocketDisconnect:
        manager.disconnect_dashboard(websocket)
    except Exception as e:
        logger.exception("Dashboard stream error", error=str(e))
        manager.disconnect_dashboard(websocket)


# Helper functions to send updates (called from other parts of the app)

async def notify_transcript(call_id: str, speaker: str, text: str, is_final: bool):
    """Notify WebSocket clients of a transcript update."""
    manager = get_connection_manager()
    await manager.send_to_call(call_id, {
        "type": "transcript",
        "data": {
            "speaker": speaker,
            "text": text,
            "is_final": is_final,
        },
    })


async def notify_agent_response(call_id: str, agent_id: str, text: str):
    """Notify WebSocket clients of an agent response."""
    manager = get_connection_manager()
    await manager.send_to_call(call_id, {
        "type": "agent_response",
        "data": {
            "agent_id": agent_id,
            "text": text,
        },
    })


async def notify_call_event(call_id: str, event_type: str, data: dict[str, Any]):
    """Notify WebSocket clients of a call event."""
    manager = get_connection_manager()
    
    # Send to call-specific connections
    await manager.send_to_call(call_id, {
        "type": "event",
        "data": {
            "event_type": event_type,
            **data,
        },
    })
    
    # Also broadcast to dashboards for certain events
    if event_type in ("call_started", "call_ended", "agent_transfer"):
        await manager.broadcast_to_dashboards({
            "type": event_type,
            "data": {
                "call_id": call_id,
                **data,
            },
        })
