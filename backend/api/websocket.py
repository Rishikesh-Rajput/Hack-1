"""WebSocket manager for real-time simulation state distribution."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Set

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("atcds.websocket")


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts snapshots."""

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total clients: {len(self.active_connections)}")

    async def disconnect(self, websocket: WebSocket) -> None:
        """Unregister a disconnected WebSocket connection."""
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(f"WebSocket client disconnected. Total clients: {len(self.active_connections)}")

    async def broadcast_json(self, data: dict) -> None:
        """Broadcast JSON payload to all active clients, pruning stale sockets."""
        if not self.active_connections:
            return

        dead_connections: Set[WebSocket] = set()
        text_data = json.dumps(data)

        async with self._lock:
            for connection in list(self.active_connections):
                try:
                    await connection.send_text(text_data)
                except Exception:
                    dead_connections.add(connection)

            for dead in dead_connections:
                self.active_connections.discard(dead)


ws_manager = ConnectionManager()
