from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.ws import ws_manager


router = APIRouter(prefix="/debug", tags=["debug"])


class TestSignalIn(BaseModel):
    symbol: str = Field(default="AAPL")
    direction: str = Field(default="LONG", pattern="^(LONG|SHORT)$")
    stop_loss_pct: float = Field(default=2.0, gt=0)
    take_profit_pct: float = Field(default=6.0, gt=0)


@router.post("/broadcast_test_signal")
async def broadcast_test_signal(body: TestSignalIn) -> dict:
    payload = {
        "id": str(uuid.uuid4()),
        "type": "ENTRY",
        "direction": body.direction,
        "symbol": body.symbol,
        "risk_params": {
            "stop_loss_pct": float(body.stop_loss_pct),
            "take_profit_pct": float(body.take_profit_pct),
        },
        "debug": True,
        "ts_utc": datetime.now(tz=UTC).isoformat(),
    }
    sent = await ws_manager.broadcast({"type": "SIGNAL", "payload": payload})
    return {"ok": True, "sent_to_clients": sent, "payload": payload}

