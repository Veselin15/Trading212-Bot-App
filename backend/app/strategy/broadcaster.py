from __future__ import annotations

from app.api.ws import ws_manager


async def broadcast_signal(payload: dict) -> int:
    return await ws_manager.broadcast({"type": "SIGNAL", "payload": payload})

