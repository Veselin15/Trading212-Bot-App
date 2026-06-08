"""Standalone strategy runner for Windows (or any capable machine).

Runs the XGBoost+LightGBM ML engine locally and pushes signals to the backend
server over HTTP, instead of broadcasting from inside the same process.

Usage (from the repo root)::

    pip install -r backend/requirements.txt
    pip install -r Server-App/requirements.txt

    set SIGNAL_PUSH_URL=https://signals.swifttrade.app
    set SIGNAL_PUSH_KEY=your-secret-key-from-deploy-.env

    python -m backend.app.strategy.t212_miner_runner_remote

Environment variables:
    SIGNAL_PUSH_URL   Base URL of the backend (default: https://signals.swifttrade.app)
    SIGNAL_PUSH_KEY   Must match SIGNAL_PUSH_KEY in server's deploy/.env
    BOT_SCHEDULE_MINUTES   Cycle interval in minutes (default: 5)
    BOT_SIGNAL_BUFFER_S    Wait seconds into the new bar (default: 20)
    STARTER_CORE_SIGNALS   How many top signals go to Starter tier (default: 2)
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

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_log = logging.getLogger("runner_remote")

# ── config ─────────────────────────────────────────────────────────────────────
_PUSH_URL  = os.getenv("SIGNAL_PUSH_URL", "https://signals.swifttrade.app").rstrip("/")
_PUSH_KEY  = os.getenv("SIGNAL_PUSH_KEY", "").strip()
_SCHEDULE_MINUTES    = int(os.getenv("BOT_SCHEDULE_MINUTES", "5").strip() or "5")
_SIGNAL_BUFFER_S     = int(os.getenv("BOT_SIGNAL_BUFFER_S",  "20"))
_MAX_JITTER_S        = float(os.getenv("BOT_JITTER_S",       "3.0"))
_STARTER_CORE        = int(os.getenv("STARTER_CORE_SIGNALS", "2").strip() or "2")

# ── sys.path: add Server-App/ so t212_miner_bot is importable ─────────────────
def _add_server_app_to_path() -> None:
    here = Path(__file__).resolve()
    # repo root is 4 levels up from this file
    repo_root = here.parents[3]
    server_app = repo_root / "Server-App"
    if not server_app.is_dir():
        _log.error("Server-App/ not found at %s — check your working directory.", server_app)
        sys.exit(1)
    if str(server_app) not in sys.path:
        sys.path.insert(0, str(server_app))

# ── timing helpers ─────────────────────────────────────────────────────────────
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

# ── HTTP push helpers ──────────────────────────────────────────────────────────
_HEADERS = {"X-Signal-Key": _PUSH_KEY, "Content-Type": "application/json"}

async def _push_signal(client: httpx.AsyncClient, payload: dict) -> None:
    try:
        resp = await client.post(f"{_PUSH_URL}/api/signal/push", json=payload, headers=_HEADERS, timeout=10.0)
        if resp.status_code == 200:
            _log.info("  ✓ Signal pushed: %s  conf=%.3f", payload.get("symbol"), payload.get("confidence", 0))
        else:
            _log.warning("  Push returned %s: %s", resp.status_code, resp.text[:120])
    except Exception as exc:
        _log.warning("  Push failed: %s", exc)

async def _push_snapshot(client: httpx.AsyncClient, snapshot: dict) -> None:
    try:
        resp = await client.post(f"{_PUSH_URL}/api/signal/snapshot", json=snapshot, headers=_HEADERS, timeout=10.0)
        if resp.status_code != 200:
            _log.debug("Snapshot push returned %s", resp.status_code)
    except Exception as exc:
        _log.debug("Snapshot push failed: %s", exc)

# ── signal builder ─────────────────────────────────────────────────────────────
def _build_signal(
    *,
    symbol: str,
    bar_ts: str,
    side: str,
    entry_price: float,
    take_profit: float,
    stop_loss: float,
    confidence: float,
    atr: float,
    min_tier: str = "starter",
) -> dict[str, Any]:
    sl_pct = abs(entry_price - stop_loss)   / entry_price * 100
    tp_pct = abs(take_profit - entry_price) / entry_price * 100
    return {
        "id":        f"{symbol}:{bar_ts}:{side}",
        "type":      "ENTRY",
        "direction": "LONG" if side == "long" else "SHORT",
        "symbol":    symbol,
        "confidence": round(confidence, 4),
        "atr":       round(atr, 6),
        "min_tier":  min_tier,
        "risk_params": {
            "stop_loss_pct":   round(sl_pct, 4),
            "take_profit_pct": round(tp_pct, 4),
        },
    }

# ── sync signal cycle (runs in thread so it doesn't block the event loop) ──────
def _run_signal_cycle(models: dict, strategy: Any, allow_entries: bool) -> dict[str, Any]:
    import numpy as np
    from t212_miner_bot.config import (
        SYMBOL_THRESHOLDS, EXEC_TP_ATR_MULT, EXEC_SL_ATR_MULT,
        MAX_OPEN_POSITIONS, SECTOR_CLAMPING_ENABLED, SYMBOL_SECTOR,
    )
    from t212_miner_bot.features import (
        compute_all_features, get_feature_columns,
        compute_sector_relative_strength, attach_sector_rs,
    )
    from t212_miner_bot.live_trader import _fetch_bars

    symbols   = list(models.keys())
    all_15m: dict = {}
    all_5m:  dict = {}

    _log.debug("Fetching bars for %d symbols…", len(symbols))
    for sym in symbols:
        bars = _fetch_bars(sym)
        if bars is None:
            continue
        all_15m[sym] = bars["15m"]
        all_5m[sym]  = bars.get("5m")
        time.sleep(0.30)

    if not all_15m:
        _log.warning("No bars fetched this cycle")
        return {"signals": [], "snapshot": {}}

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

    snapshot: dict[str, Any] = {}
    for sym, df in feat_data.items():
        score     = scores.get(sym, 0.0)
        threshold = SYMBOL_THRESHOLDS.get(sym, 0.70)
        passes    = score >= threshold
        snapshot[sym] = {
            "ready":       True,
            "timestamp":   str(df.index[-1]),
            "confidence":  round(score, 4),
            "threshold":   threshold,
            "signal_side": "long" if (passes and allow_entries) else "none",
            "regime_frac": round(regime_frac, 3),
            "market_open": True,
        }

    if not allow_entries:
        return {"signals": [], "snapshot": snapshot}

    signals: list[dict[str, Any]] = []
    open_sectors: set = set()

    for sym, df in sorted(feat_data.items(), key=lambda x: -scores.get(x[0], 0)):
        if len(signals) >= MAX_OPEN_POSITIONS:
            break
        score     = scores.get(sym, 0.0)
        threshold = SYMBOL_THRESHOLDS.get(sym, 0.70)
        if score < threshold:
            continue
        if SECTOR_CLAMPING_ENABLED:
            sector = SYMBOL_SECTOR.get(sym)
            if sector and sector in open_sectors:
                continue
        last   = df.iloc[-1]
        bar_ts = str(df.index[-1])
        try:
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

        min_tier = "starter" if len(signals) < _STARTER_CORE else "pro"
        signals.append(_build_signal(
            symbol=sym, bar_ts=bar_ts, side="long",
            entry_price=float(signal_obj.entry_price),
            take_profit=float(signal_obj.take_profit),
            stop_loss=float(signal_obj.stop_loss),
            confidence=score, atr=float(signal_obj.atr),
            min_tier=min_tier,
        ))
        if SECTOR_CLAMPING_ENABLED:
            sector = SYMBOL_SECTOR.get(sym)
            if sector:
                open_sectors.add(sector)

    return {"signals": signals, "snapshot": snapshot}

# ── main async loop ────────────────────────────────────────────────────────────
async def run_forever() -> None:
    if not _PUSH_KEY:
        _log.error("SIGNAL_PUSH_KEY is not set. Export it before running.")
        sys.exit(1)

    _add_server_app_to_path()

    try:
        from t212_miner_bot.config import EU_SYMBOLS
        from t212_miner_bot.ensemble_model import EnsembleModel
        from t212_miner_bot.production import PRODUCTION_BLOCKLIST, build_strategy
    except ImportError as exc:
        _log.error("t212_miner_bot import failed: %s", exc)
        sys.exit(1)

    models: dict = {}
    available = [s for s in EU_SYMBOLS if s not in PRODUCTION_BLOCKLIST]
    for sym in available:
        try:
            models[sym] = EnsembleModel.load(sym)
        except Exception:
            pass

    if not models:
        _log.error("No trained models found in Server-App/t212_miner_bot/models/")
        sys.exit(1)

    strategy = build_strategy()
    _log.info("Strategy runner started — %d / %d models loaded. Pushing to %s",
              len(models), len(available), _PUSH_URL)

    last_emitted: dict[str, str] = {}

    async with httpx.AsyncClient() as client:
        while True:
            wait_s = _seconds_until_next_schedule()
            _log.info("Sleeping %.0fs until next 5m tick…", wait_s)
            await asyncio.sleep(wait_s)

            now_utc       = _now_utc()
            allow_entries = _is_new_15m_close(now_utc)
            tick_tag      = "ENTRY" if allow_entries else "MGMT"
            _log.info("Cycle %s UTC [%s]", now_utc.strftime("%Y-%m-%d %H:%M"), tick_tag)

            try:
                loop   = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, _run_signal_cycle, models, strategy, allow_entries
                )
            except Exception as exc:
                _log.exception("Cycle error: %s", exc)
                continue

            await _push_snapshot(client, result.get("snapshot", {}))

            for sig in result.get("signals", []):
                sig_id = sig.get("id", "")
                sym    = sig.get("symbol", "")
                if sig_id and last_emitted.get(sym) == sig_id:
                    continue
                await _push_signal(client, sig)
                if sig_id:
                    last_emitted[sym] = sig_id


if __name__ == "__main__":
    asyncio.run(run_forever())
