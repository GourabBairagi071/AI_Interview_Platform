import asyncio
import json
import logging
from typing import Any
import uuid

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages active authenticated WebSocket connections across multiple tabs/devices per user.
    Provides robust, isolated event distribution by user, role, or broadcast.
    """

    def __init__(self):
        # user_id string -> set of active WebSockets
        self.active_connections: dict[str, set[WebSocket]] = {}
        # user_id string -> role (e.g. "admin", "candidate")
        self.user_roles: dict[str, str] = {}
        # Lock for mutating connections dictionary
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str, role: str = "candidate") -> None:
        """Register a new active WebSocket connection for a user."""
        await websocket.accept()
        async with self._lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
            self.user_roles[user_id] = role

        logger.info(
            "WebSocket connected for user %s (role: %s). Total connections for user: %d",
            user_id,
            role,
            len(self.active_connections[user_id]),
        )

    async def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        """Remove a disconnected WebSocket."""
        async with self._lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
                    self.user_roles.pop(user_id, None)

        logger.info("WebSocket disconnected for user %s", user_id)

    async def send_personal(self, websocket: WebSocket, event_data: dict[str, Any]) -> bool:
        """Send an event directly to a specific socket."""
        try:
            payload = json.dumps(event_data)
            await websocket.send_text(payload)
            return True
        except Exception as e:
            logger.warning("Failed to send message to WebSocket: %s", e)
            return False

    async def broadcast_to_user(self, user_id: str | uuid.UUID, event_data: dict[str, Any]) -> int:
        """
        Deliver event to all active connections for a given user.
        Safely purges stale/dead sockets without failing.
        """
        uid = str(user_id)
        async with self._lock:
            sockets = list(self.active_connections.get(uid, set()))

        if not sockets:
            return 0

        payload = json.dumps(event_data)
        stale_sockets: list[WebSocket] = []
        sent_count = 0

        for ws in sockets:
            try:
                await ws.send_text(payload)
                sent_count += 1
            except Exception as e:
                logger.warning("Error dispatching to user %s connection, marking stale: %s", uid, e)
                stale_sockets.append(ws)

        if stale_sockets:
            async with self._lock:
                for dead_ws in stale_sockets:
                    if uid in self.active_connections:
                        self.active_connections[uid].discard(dead_ws)
                if uid in self.active_connections and not self.active_connections[uid]:
                    del self.active_connections[uid]
                    self.user_roles.pop(uid, None)

        return sent_count

    async def broadcast_to_role(self, role: str, event_data: dict[str, Any]) -> int:
        """Deliver event to all connected users with a given role."""
        async with self._lock:
            target_users = [uid for uid, r in self.user_roles.items() if r == role]

        total_sent = 0
        for uid in target_users:
            total_sent += await self.broadcast_to_user(uid, event_data)
        return total_sent

    async def broadcast(self, event_data: dict[str, Any]) -> int:
        """Deliver event to all connected users across the platform."""
        async with self._lock:
            all_users = list(self.active_connections.keys())

        total_sent = 0
        for uid in all_users:
            total_sent += await self.broadcast_to_user(uid, event_data)
        return total_sent

    def is_user_connected(self, user_id: str | uuid.UUID) -> bool:
        """Check if a given user currently has at least one active connection."""
        uid = str(user_id)
        return bool(self.active_connections.get(uid))

    def get_connection_count(self) -> int:
        """Return total active sockets across all users."""
        return sum(len(socks) for socks in self.active_connections.values())

    def get_user_count(self) -> int:
        """Return total unique users currently connected."""
        return len(self.active_connections)


# Global singleton ConnectionManager instance
connection_manager = ConnectionManager()
