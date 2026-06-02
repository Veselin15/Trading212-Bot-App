"""Strategy runner for new_trading212bot v2 – ML-based EU swing bot.

Bridges the FastAPI WebSocket backend with the AI-Trading/new_trading212bot
ML trading engine.  Runs as a FastAPI background task; reads live market data
via yfinance/TwelveData, generates XGBoost+LightGBM ensemble signals, and
broadcasts them over WebSocket to connected desktop executor apps.

This module does NOT place any orders — the desktop executor does that.
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.strategy.broadcaster import broadcast_signal
from app.api.ws import ws_manager

_log = logging.getLogger("uvicorn.error")


# ---------------------------------------------------------------------------
# sys.path injection
# ---------------------------------------------------------------------------

def _add_new_bot_to_syspath() -> None:
    """Add AI-Trading/ to sys.path so new_trading212bot is importable."""
    here = Path(__file__).resolve()
    # Trading212-Bot-App is 4 levels up from this file
    repo_root = here.parents[3]
    # new_trading212bot lives in the sibling AI-Trading/ directory
    ai_trading = repo_root.parent / "AI-Trading"
    if str(ai_trading) not in sys.path:
        sys.path.insert(0, str(ai_trading))


# ---------------------------------------------------------------------------
# Timing helpers
# ---------------------------------------------------------------------------

_SCHEDULE_MINUTES = int(os.getenv("BOT_SCHEDULE_MINUTES", "5").strip() or "5")
_SIGNAL_BUFFER_S  = int(os.getenv("BOT_SIGNAL_BUFFER_S", "20"))
_MAX_JITTER_S     = float(os.getenv("BOT_JITTER_S", "3.0"))


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


def _seconds_until_next_schedule() -> float:
    now = _now_utc()
    rem = now.minute % _SCHEDULE_MINUTES
    wait_min = (_SCHEDULE_MINUTES - rem) if rem > 0 else _SCHEDULE_MINUTES
    wait_sec = wait_min * 60 - (now.second + now.microsecond / 1e6)
    return max(wait_sec + _SIGNAL_BUFFER_S + random.uniform(0, _MAX_JITTER_S), 1.0)


def _is_new_15m_close(ts_utc: datetime) -> bool:
    return (ts_utc.minute % 15) == 0


# ---------------------------------------------------------------------------
# Signal format helpers
# ---------------------------------------------------------------------------

def _build_entry_signal(
    *,
    symbol: str,
    bar_ts: str,
    side: str,
    entry_price: float,
    take_profit: float,
    stop_loss: float,
    confidence: float,
    atr: float,
) -> dict[str, Any]:
    stop_loss_pct   = abs(entry_price - stop_loss)   / entry_price * 100
    take_profit_pct = abs(take_profit - entry_price) / entry_price * 100
    trade_id = f"{symbol}:{bar_ts}:{side}"
    return {
        "id":        trade_id,
        "type":      "ENTRY",
        "direction": "LONG" if side == "long" else "SHORT",
        "symbol":    symbol,
        "confidence": round(confidence, 4),
        "atr":       round(atr, 6),
        "risk_params": {
            "stop_loss_pct":   round(stop_loss_pct,   4),
            "take_profit_pct": round(take_profit_pct, 4),
        },
    }


# ---------------------------------------------------------------------------
# Sync cycle (runs in a thread executor so it doesn't block the event loop)
# ---------------------------------------------------------------------------

def _run_signal_cycle(
    models:   dict,
    strategy: Any,
    allow_entries: bool,
) -> dict[str, Any]:
    """
    Fetch live bars, compute features, run ML inference, apply entry filters.
    Returns a dict:  {"signals": [...], "snapshot": {...}}
    """
    import numpy as np

    from new_trading212bot.config import (
        SYMBOL_THRESHOLDS,
        EXEC_TP_ATR_MULT,
        EXEC_SL_ATR_MULT,
        MAX_OPEN_POSITIONS,
        SECTOR_CLAMPING_ENABLED,
        SYMBOL_SECTOR,
    )
    from new_trading212bot.features import (
        compute_all_features,
        get_feature_columns,
        compute_sector_relative_strength,
        attach_sector_rs,
    )

    symbols = list(models.keys())
    all_15m: dict = {}
    all_5m:  dict = {}

    # Import fetch_bars lazily (imports yfinance which may be slow)
    from new_trading212bot.live_trader import _fetch_bars

    _log.debug("Fetching bars for %d symbols…", len(symbols))
    for sym in symbols:
        bars = _fetch_bars(sym)
        if bars is None:
            continue
        all_15m[sym] = bars["15m"]
        all_5m[sym]  = bars.get("5m")
        time.sleep(0.30)

    if not all_15m:
        _log.warning("new_trading212bot: no bars fetched this cycle")
        return {"signals": [], "snapshot": {}}

    # Compute features
    sector_rs = compute_sector_relative_strength(all_15m)
    feat_data: dict = {}
    for sym, df15 in all_15m.items():
        df = df15.copy()
        try:
            compute_all_features(df, all_5m.get(sym), symbol=sym)
            attach_sector_rs(df, sector_rs.get(sym, None))
            feat_data[sym] = df
        except Exception as exc:
            _log.warning("  [%s] feature computation failed: %s", sym, exc)

    # ML inference
    scores: dict[str, float] = {}
    for sym, df in feat_data.items():
        model = models.get(sym)
        if model is None or df.empty:
            continue
        try:
            fcols = [c for c in get_feature_columns(df) if not df[c].isna().all()]
            X     = df[fcols].fillna(0.0)
            proba = model.predict_proba(X)
            scores[sym] = float(proba[-1])
        except Exception as exc:
            _log.warning("  [%s] inference failed: %s", sym, exc)

    # Macro regime fraction (fraction of universe above EMA200)
    above = sum(
        1 for sym, df in feat_data.items()
        if "ema_200" in df.columns and not df.empty
        and not np.isnan(float(df["ema_200"].iloc[-1]))
        and float(df["close"].iloc[-1]) >= float(df["ema_200"].iloc[-1])
    )
    total_with_ema = sum(
        1 for sym, df in feat_data.items()
        if "ema_200" in df.columns and not df.empty
        and not np.isnan(float(df["ema_200"].iloc[-1]))
    )
    regime_frac = above / total_with_ema if total_with_ema > 0 else 1.0

    # Build snapshot
    snapshot: dict[str, Any] = {}
    for sym, df in feat_data.items():
        last = df.iloc[-1]
        score = scores.get(sym, 0.0)
        threshold = SYMBOL_THRESHOLDS.get(sym, 0.70)
        passes = score >= threshold
        snapshot[sym] = {
            "ready":        True,
            "timestamp":    str(df.index[-1]),
            "confidence":   round(score, 4),
            "threshold":    threshold,
            "signal_side":  "long" if (passes and allow_entries) else "none",
            "regime_frac":  round(regime_frac, 3),
            "market_open":  True,
        }

    if not allow_entries:
        return {"signals": [], "snapshot": snapshot}

    # Generate entry signals (apply filters the same way strategy.generate_signal does)
    signals: list[dict[str, Any]] = []
    open_sectors: set = set()

    for sym, df in sorted(feat_data.items(), key=lambda x: -scores.get(x[0], 0)):
        if len(signals) >= MAX_OPEN_POSITIONS:
            break

        score = scores.get(sym, 0.0)
        threshold = SYMBOL_THRESHOLDS.get(sym, 0.70)
        if score < threshold:
            continue

        if SECTOR_CLAMPING_ENABLED:
            sector = SYMBOL_SECTOR.get(sym)
            if sector and sector in open_sectors:
                continue

        last = df.iloc[-1]
        try:
            bar_ts = str(df.index[-1])
            signal_obj = strategy.generate_signal(
                sym, last, score, set(),
                bars_since_last_trade=999,
                threshold_override=threshold,
                last_exit_was_win=True,
            )
        except Exception as exc:
            _log.warning("  [%s] generate_signal failed: %s", sym, exc)
            continue

        if signal_obj is None:
            continue

        sig = _build_entry_signal(
            symbol=sym,
            bar_ts=bar_ts,
            side="long",
            entry_price=float(signal_obj.entry_price),
            take_profit=float(signal_obj.take_profit),
            stop_loss=float(signal_obj.stop_loss),
            confidence=score,
            atr=float(signal_obj.atr),
        )
        signals.append(sig)

        if SECTOR_CLAMPING_ENABLED:
            sector = SYMBOL_SECTOR.get(sym)
            if sector:
                open_sectors.add(sector)

    return {"signals": signals, "snapshot": snapshot}


# ---------------------------------------------------------------------------
# Async forever loop
# ---------------------------------------------------------------------------

async def run_t212_miner_strategy_forever() -> None:
    """FastAPI background task: generates and broadcasts ML trading signals."""
    _add_new_bot_to_syspath()

    try:
        from new_trading212bot.config import EU_SYMBOLS
        from new_trading212bot.ensemble_model import EnsembleModel
        from new_trading212bot.production import PRODUCTION_BLOCKLIST, build_strategy
    except ImportError as exc:
        _log.error(
            "new_trading212bot import failed – is AI-Trading/ present? (%s). "
            "Strategy runner will not start.",
            exc,
        )
        return

    # Load trained ML models
    models: dict = {}
    available = [s for s in EU_SYMBOLS if s not in PRODUCTION_BLOCKLIST]
    for sym in available:
        try:
            models[sym] = EnsembleModel.load(sym)
        except Exception:
            pass

    if not models:
        _log.warning(
            "new_trading212bot: no trained models found under AI-Trading/new_trading212bot/models/. "
            "Run run_pipeline.py to train models. Strategy runner idle."
        )
        return

    strategy = build_strategy()
    _log.info(
        "new_trading212bot strategy runner started: %d / %d models loaded.",
        len(models), len(available),
    )

    last_emitted_by_symbol: dict[str, str] = {}

    while True:
        wait_s = _seconds_until_next_schedule()
        _log.debug("new_trading212bot: sleeping %.0fs until next 5m tick…", wait_s)
        await asyncio.sleep(wait_s)

        now_utc   = _now_utc()
        allow_entries = _is_new_15m_close(now_utc)
        tick_tag  = "ENTRY" if allow_entries else "MGMT"
        _log.info(
            "new_trading212bot cycle (%s UTC) [%s]",
            now_utc.strftime("%Y-%m-%d %H:%M"),
            tick_tag,
        )

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, _run_signal_cycle, models, strategy, allow_entries,
            )
        except Exception as exc:
            _log.exception("new_trading212bot cycle error: %s", exc)
            continue

        # Always broadcast snapshot so the desktop can show bot state
        await ws_manager.broadcast({
            "type":    "BOT_SNAPSHOT",
            "payload": result.get("snapshot", {}),
        })

        # Broadcast entry signals (deduplicate by id to avoid re-sending same bar)
        for sig in result.get("signals", []):
            sig_id = sig.get("id", "")
            sym    = sig.get("symbol", "")
            if sig_id and last_emitted_by_symbol.get(sym) == sig_id:
                continue
            await broadcast_signal(sig)
            if sig_id:
                last_emitted_by_symbol[sym] = sig_id
            _log.info(
                "  Signal broadcast: %s  conf=%.3f  TP=%.2f%%  SL=%.2f%%",
                sym,
                sig.get("confidence", 0),
                sig.get("risk_params", {}).get("take_profit_pct", 0),
                sig.get("risk_params", {}).get("stop_loss_pct", 0),
            )
