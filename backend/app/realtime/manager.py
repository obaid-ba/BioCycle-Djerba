"""WebSocket connection manager.

A process-local registry of active dashboard connections with a fan-out
`broadcast`. Single-process by design for the MVP; scaling to multiple workers
later means swapping this for a Redis/pub-sub backplane behind the same
interface (the rest of the app only depends on `manager.broadcast`).
"""

from typing import Any, Protocol

from app.core.logging import get_logger

logger = get_logger(__name__)


class _WebSocketLike(Protocol):
    async def accept(self) -> None: ...
    async def send_json(self, data: Any) -> None: ...


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[_WebSocketLike] = set()

    @property
    def count(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: _WebSocketLike) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        logger.info("WebSocket connected (%d active)", self.count)

    def disconnect(self, websocket: _WebSocketLike) -> None:
        self._connections.discard(websocket)
        logger.info("WebSocket disconnected (%d active)", self.count)

    async def broadcast(self, message: dict) -> None:
        dead: list[_WebSocketLike] = []
        for connection in list(self._connections):
            try:
                await connection.send_json(message)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)


# Process-wide singleton used by both the WebSocket route and the publishers.
manager = ConnectionManager()
