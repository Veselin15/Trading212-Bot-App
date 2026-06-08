"""Remote signal push endpoint.

Allows an external strategy runner (e.g. running on a capable Windows machine)
to broadcast signals to all connected desktop clients via HTTP POST rather than
requiring the strategy runner to run inside the same process as the backend.

Authentication: ``X-Signal-Key`` header must match ``SIGNAL_PUSH_KEY`` env var.
Enable:  set SIGNAL_PUSH_ENABLED=true and SIGNAL_PUSH_KEY=<long-random-secret>
         in deploy/.env.  Off by default so the endpoint is not exposed without
         explicit opt-in.
"""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.api.ws import ws_manager
from app.strategy.broadcaster import broadcast_signal

router = APIRouter(prefix="/api/signal", tags=["signal-push"])

_ENABLED = os.getenv("SIGNAL_PUSH_ENABLED", "false").strip().lower() == "true"
_KEY = os.getenv("SIGNAL_PUSH_KEY", "").strip()


async def _require_key(request: Request) -> None:
    if not _ENABLED:
        raise HTTPException(status_code=404, detail="Not found")
    provided = (request.headers.get("X-Signal-Key") or "").strip()
    if not _KEY or provided != _KEY:
        raise HTTPException(status_code=403, detail="Forbidden")


class SignalIn(BaseModel):
    id: str
    type: str = "ENTRY"
    direction: str = Field(pattern="^(LONG|SHORT)$")
    symbol: str
    confidence: float = 0.0
    atr: float = 0.0
    min_tier: str = "starter"
    risk_params: dict = Field(default_factory=dict)


@router.post("/push", dependencies=[Depends(_require_key)])
async def push_signal(body: SignalIn) -> dict:
    """
    Broadcast a trading signal to all connected desktop clients.

    Called by the external strategy runner (e.g. on Windows) when the backend
    server is running on a CPU that cannot execute xgboost/lightgbm inference.

    Example::

        curl -X POST https://signals.swifttrade.app/api/signal/push \\
             -H "X-Signal-Key: YOUR_SECRET" \\
             -H "Content-Type: application/json" \\
             -d '{"id":"abc","direction":"LONG","symbol":"ASML.AS","min_tier":"starter",...}'
    """
    payload = body.model_dump()
    sent = await broadcast_signal(payload)
    return {"ok": True, "sent_to_clients": sent}


@router.post("/snapshot", dependencies=[Depends(_require_key)])
async def push_snapshot(request: Request) -> dict:
    """Broadcast a BOT_SNAPSHOT payload (bot state for the Live feed tab)."""
    data = await request.json()
    sent = await ws_manager.broadcast({"type": "BOT_SNAPSHOT", "payload": data})
    return {"ok": True, "sent_to_clients": sent}
