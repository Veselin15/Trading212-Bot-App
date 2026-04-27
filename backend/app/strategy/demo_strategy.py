from __future__ import annotations

import asyncio
import uuid

from app.strategy.broadcaster import broadcast_signal


async def run_demo_strategy() -> None:
    # Placeholder strategy loop to validate the end-to-end pipeline.
    # Real strategy integration will wrap your existing `Server-App/t212_miner_bot` signal generation.
    while True:
        await asyncio.sleep(15.0)
        payload = {
            "id": str(uuid.uuid4()),
            "type": "ENTRY",
            "direction": "LONG",
            "symbol": "AAPL",
            "risk_params": {"stop_loss_pct": 2.0, "take_profit_pct": 6.0},
        }
        await broadcast_signal(payload)

