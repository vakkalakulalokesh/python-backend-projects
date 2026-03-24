import json
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: list[tuple[WebSocket, UUID | None]] = []

    async def connect(self, websocket: WebSocket, source_filter: UUID | None) -> None:
        await websocket.accept()
        self._connections.append((websocket, source_filter))

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections = [
            (ws, f) for ws, f in self._connections if ws is not websocket
        ]

    async def broadcast(self, message: dict[str, Any]) -> None:
        payload = json.dumps(message, default=str)
        dead: list[WebSocket] = []
        for ws, src_filter in self._connections:
            try:
                data = message.get("payload") or {}
                sid = data.get("source_id")
                if src_filter is not None and sid is not None:
                    if str(src_filter) != str(sid):
                        continue
                await ws.send_text(payload)
            except Exception:
                logger.debug("websocket send failed", exc_info=True)
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


@router.websocket("/ws/alerts")
async def alerts_ws(websocket: WebSocket, source_id: UUID | None = None) -> None:
    await manager.connect(websocket, source_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
