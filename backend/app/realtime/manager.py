"""WebSocket connection manager.

A process-local registry of active dashboard connections with a fan-out
`broadcast` plus a per-user index for targeted delivery (`send_to_user`).
Single-process by design for the MVP; scaling to multiple workers later means
swapping this for a Redis/pub-sub backplane behind the same interface (the rest
of the app only depends on `broadcast` / `send_to_user`).
"""

import uuid
from typing import Any, Protocol

from app.core.logging import get_logger

logger = get_logger(__name__)


class _WebSocketLike(Protocol):
    async def accept(self) -> None: ...
    async def send_json(self, data: Any) -> None: ...


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[_WebSocketLike] = set()
        # Index by user so we can push a notification to just that user's
        # tabs/devices. One user may hold several connections.
        self._by_user: dict[uuid.UUID, set[_WebSocketLike]] = {}

    @property
    def count(self) -> int:
        return len(self._connections)

    async def connect(
        self, websocket: _WebSocketLike, user_id: uuid.UUID | None = None
    ) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        if user_id is not None:
            self._by_user.setdefault(user_id, set()).add(websocket)
        logger.info("WebSocket connected (%d active)", self.count)

    def disconnect(self, websocket: _WebSocketLike) -> None:
        self._connections.discard(websocket)
        # Drop from every user bucket it appears in, cleaning up empties.
        for user_id, conns in list(self._by_user.items()):
            conns.discard(websocket)
            if not conns:
                del self._by_user[user_id]
        logger.info("WebSocket disconnected (%d active)", self.count)

    async def _send(self, connection: _WebSocketLike, message: dict) -> bool:
        try:
            await connection.send_json(message)
            return True
        except Exception:
            return False

    async def broadcast(self, message: dict) -> None:
        dead = [c for c in list(self._connections) if not await self._send(c, message)]
        for connection in dead:
            self.disconnect(connection)

    async def send_to_user(self, user_id: uuid.UUID, message: dict) -> None:
        """Deliver a message to all of one user's live connections (if any)."""
        conns = self._by_user.get(user_id)
        if not conns:
            return
        dead = [c for c in list(conns) if not await self._send(c, message)]
        for connection in dead:
            self.disconnect(connection)


# Process-wide singleton used by both the WebSocket route and the publishers.
manager = ConnectionManager()
