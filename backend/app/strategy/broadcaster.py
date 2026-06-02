from __future__ import annotations

from app.api.ws import ws_manager
from app.services.tiers import required_level_for_signal


async def broadcast_signal(payload: dict) -> int:
    """Broadcast a trading signal, gated by its ``min_tier`` tag.

    A signal tagged ``min_tier="pro"`` is only delivered to connections entitled to
    the extended feed (Pro + Trial); ``min_tier="starter"`` (the default) reaches all
    paid/trial connections.
    """
    min_tier = payload.get("min_tier")
    level = required_level_for_signal(min_tier)
    return await ws_manager.broadcast({"type": "SIGNAL", "payload": payload}, min_signal_level=level)
