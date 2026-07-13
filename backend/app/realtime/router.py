"""WebSocket endpoint for the realtime dashboard.

Browsers can't set Authorization headers on WebSocket handshakes, so the JWT is
passed as a `?token=` query param and validated before the socket is accepted.
"""

import uuid

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

    # Associate the connection with its user so notifications can be targeted.
    subject = payload.get("sub")
    try:
        user_id = uuid.UUID(subject) if subject else None
    except (ValueError, TypeError):
        user_id = None

    await manager.connect(websocket, user_id=user_id)
    await websocket.send_json({"type": "connection.ack"})
    try:
        # We don't expect client messages; receive loop keeps the socket open
        # and detects disconnects.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
