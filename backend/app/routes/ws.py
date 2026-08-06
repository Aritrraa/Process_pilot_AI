import json
from typing import Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging

logger = logging.getLogger("processpilot.ws")
router = APIRouter(prefix="/ws", tags=["websockets"])

class ConnectionManager:
    """
    In-memory WebSocket Connection Manager.
    (Best for single-server deployments like Render Free Tier).
    """
    def __init__(self):
        # Maps user_id to a list of active WebSocket connections
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: str, user_id: int):
        """Sends a message only to WebSockets connected to this instance."""
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message)
                except Exception:
                    pass

    async def broadcast(self, message: str):
        """Broadcasts only to WebSockets connected to this instance."""
        for connections in self.active_connections.values():
            for connection in connections:
                try:
                    await connection.send_text(message)
                except Exception:
                    pass

manager = ConnectionManager()

@router.websocket("/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(websocket, user_id)
    try:
        while True:
            # Keep connection open to push events
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
