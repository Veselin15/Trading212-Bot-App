from __future__ import annotations

import asyncio
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.strategy.broadcaster import broadcast_signal
from app.api.ws import ws_manager


def _add_server_app_to_syspath() -> None:
    """
    The original bot lives under `Server-App/t212_miner_bot`.
    The backend runs with PYTHONPATH=backend, so we extend sys.path at runtime.
    """
    here = Path(__file__).resolve()
    repo_root = here.parents[3]  # .../Projects/Trading212-Bot-App
    server_app = repo_root / "Server-App"
    # Append (never prepend): inserting at 0 can shadow unrelated imports during the process lifetime.
    if str(server_app) not in sys.path:
        sys.path.append(str(server_app))


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


def _seconds_until_next_5m_close(*, buffer_seconds: int, jitter_max_seconds: float) -> float:
    now = _now_utc()
    next_minute = ((now.minute // 5) + 1) * 5

    if next_minute >= 60:
        target = now.replace(minute=0, second=buffer_seconds, microsecond=0) + timedelta(hours=1)
    else:
        target = now.replace(minute=next_minute, second=buffer_seconds, microsecond=0)

    if target <= now:
        target += timedelta(minutes=5)

    base = max((target - now).total_seconds(), 0.5)
    if jitter_max_seconds > 0:
        base += random.uniform(0.0, float(jitter_max_seconds))
    return base


def _signal_payload_from_snapshot(*, symbol: str, snap: dict[str, Any]) -> dict[str, Any] | None:
    side = str(snap.get("signal_side") or "none").lower()
    if side not in {"long", "short"}:
        return None

    close = float(snap.get("close") or 0.0)
    atr_5m = float(snap.get("atr_5m") or 0.0)
    if close <= 0 or atr_5m <= 0:
        return None

    # Pull bot params from the existing config.
    # Import happens here so sys.path injection has already run.
    from t212_miner_bot.config import ATR_MULTIPLIER, UNIT1_TP_RR  # type: ignore

    stop_loss_pct = (float(ATR_MULTIPLIER) * atr_5m / close) * 100.0
    take_profit_pct = stop_loss_pct * float(UNIT1_TP_RR)

    ts = str(snap.get("timestamp") or "")
    trade_id = f"{symbol}:{ts}:{side}"

    return {
        "id": trade_id,
        "type": "ENTRY",
        "direction": "LONG" if side == "long" else "SHORT",
        "symbol": symbol,
        "risk_params": {
            "stop_loss_pct": round(float(stop_loss_pct), 4),
            "take_profit_pct": round(float(take_profit_pct), 4),
        },
    }


async def run_t212_miner_strategy_forever() -> None:
    _add_server_app_to_syspath()

    from t212_miner_bot.config import SIGNAL_BUFFER_SECONDS, WAIT_JITTER_MAX_SECONDS  # type: ignore
    from t212_miner_bot.data_feed import get_latest_signals  # type: ignore

    last_emitted_by_symbol: dict[str, str] = {}

    while True:
        wait_s = _seconds_until_next_5m_close(
            buffer_seconds=int(SIGNAL_BUFFER_SECONDS),
            jitter_max_seconds=float(WAIT_JITTER_MAX_SECONDS),
        )
        await asyncio.sleep(wait_s)

        signals = await get_latest_signals()
        snapshot_payload: dict[str, dict[str, Any]] = {}
        for symbol, snap in signals.items():
            if not isinstance(snap, dict) or not snap.get("ready"):
                snapshot_payload[symbol] = {
                    "ready": bool(snap.get("ready")) if isinstance(snap, dict) else False,
                    "reason": (snap.get("reason") if isinstance(snap, dict) else "invalid_snapshot"),
                }
                continue
            snapshot_payload[symbol] = {
                "ready": True,
                "timestamp": snap.get("timestamp"),
                "regime": snap.get("regime"),
                "trigger": snap.get("trigger"),
                "signal_side": snap.get("signal_side"),
                "reason": snap.get("reason"),
                "entry_blocked": bool(snap.get("entry_blocked")),
                "bar_ts": snap.get("bar_ts"),
                "bar_age_seconds": snap.get("bar_age_seconds"),
                "market_open": snap.get("market_open"),
            }
            if snap.get("entry_blocked"):
                continue

            payload = _signal_payload_from_snapshot(symbol=symbol, snap=snap)
            if payload is None:
                continue

            # Avoid rebroadcasting the same bar.
            ts = str(snap.get("timestamp") or "")
            if ts and last_emitted_by_symbol.get(symbol) == ts:
                continue

            await broadcast_signal(payload)
            if ts:
                last_emitted_by_symbol[symbol] = ts

        # Always broadcast a lightweight snapshot so the desktop can display bot state,
        # even when no ENTRY signals are emitted (market closed, stale data, etc.).
        await ws_manager.broadcast({"type": "BOT_SNAPSHOT", "payload": snapshot_payload})

