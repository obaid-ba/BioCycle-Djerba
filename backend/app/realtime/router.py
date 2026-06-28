"""WebSocket endpoint for the realtime dashboard.

Browsers can't set Authorization headers on WebSocket handshakes, so the JWT is
passed as a `?token=` query param and validated before the socket is accepted.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.logging import get_logger
from app.core.security import TOKEN_TYPE_ACCESS, decode_token
from app.realtime.manager import manager
from app.shared.exceptions import AppException

router = APIRouter()
logger = get_logger(__name__)


@router.websocket("/ws")
async def dashboard_ws(websocket: WebSocket, token: str | None = None) -> None:
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        payload = decode_token(token)
    except AppException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    if payload.get("type") != TOKEN_TYPE_ACCESS:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await manager.connect(websocket)
    await websocket.send_json({"type": "connection.ack"})
    try:
        # We don't expect client messages; receive loop keeps the socket open
        # and detects disconnects.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
