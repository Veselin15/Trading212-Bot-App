from __future__ import annotations

import asyncio
import contextlib
import io
import logging
import random
from datetime import timedelta, time as dt_time
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yfinance as yf

from .config import (
    BAR_INTERVAL,
    EMA_PERIOD,
    ENABLE_TIME_FILTER,
    FETCH_STAGGER_SECONDS,
    LOOKBACK_BARS,
    MAX_LIVE_FETCHES_PER_CYCLE,
    STALE_BAR_GRACE_SECONDS,
    STALE_BAR_MAX_AGE_MULT,
    STALE_BAR_STRIKES_TO_PAUSE,
    SYMBOLS_MAP,
)
from .indicators import add_indicators, cross_down, cross_up

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
_LAST_GOOD_BARS: dict[str, pd.DataFrame] = {}
_STALE_STRIKES: dict[str, int] = {}
_PAUSED_FOR_STALE: set[str] = set()
_FAIL_STREAK: dict[str, int] = {}
_NEXT_RETRY_UTC: dict[str, pd.Timestamp] = {}
_NO_DATA_STREAK: dict[str, int] = {}
_NY_TZ = ZoneInfo("America/New_York")
_LUNCH_START = dt_time(11, 30)
_LUNCH_END = dt_time(13, 30)
_UTC = ZoneInfo("UTC")
_AMS_TZ = ZoneInfo("Europe/Amsterdam")
_BERLIN_TZ = ZoneInfo("Europe/Berlin")

# "Free-but-usable" mode: skip yfinance polling when exchanges are closed.
# We keep management via broker quotes in ExecutionManager, but candle-driven entries should not
# depend on off-hours yfinance gaps. These windows intentionally INCLUDE pre/after where practical.
_US_EXT_OPEN = dt_time(4, 0)
_US_EXT_CLOSE = dt_time(20, 0)
_EU_EXT_OPEN = dt_time(8, 0)
_EU_EXT_CLOSE = dt_time(18, 0)


def _flatten_yf_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        # yfinance can return MultiIndex columns depending on version/settings.
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
    return df


def _normalize_ohlcv_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    }
    out = df.rename(columns=rename_map).copy()
    required = ["open", "high", "low", "close", "volume"]
    if any(col not in out.columns for col in required):
        return pd.DataFrame(columns=required)
    return out[required].dropna(subset=["open", "high", "low", "close"])


def _bar_interval_seconds() -> float:
    raw = str(BAR_INTERVAL or "").strip().lower()
    if raw.endswith("m"):
        minutes = float(raw[:-1])
        return max(minutes * 60.0, 1.0)
    if raw.endswith("h"):
        hours = float(raw[:-1])
        return max(hours * 3600.0, 1.0)
    # Default to 5m if misconfigured.
    return 300.0


def _to_utc_timestamp(ts: pd.Timestamp) -> pd.Timestamp:
    if ts.tzinfo is None:
        return ts.tz_localize(_UTC)
    return ts.tz_convert(_UTC)


def _localize_bar_timestamp(ts: pd.Timestamp, yf_symbol: str) -> pd.Timestamp:
    """
    yfinance intraday indexes are commonly tz-naive but represent the exchange-local wall time.
    We must localize correctly per market; otherwise staleness checks are wrong by 1-2 hours.
    """
    if ts.tzinfo is not None:
        return ts
    sym = str(yf_symbol or "").upper()
    if sym.endswith(".AS"):
        return ts.tz_localize(_AMS_TZ)
    if sym.endswith(".DE"):
        return ts.tz_localize(_BERLIN_TZ)
    # Default to US market timezone for plain tickers.
    return ts.tz_localize(_NY_TZ)


def _is_stale_last_bar(last_bar_ts: pd.Timestamp, yf_symbol: str) -> tuple[bool, float]:
    now = pd.Timestamp.now(tz=_UTC)
    last_local = _localize_bar_timestamp(last_bar_ts, yf_symbol=yf_symbol)
    last_utc = _to_utc_timestamp(last_local)
    age_seconds = float((now - last_utc).total_seconds())
    max_age = float(STALE_BAR_MAX_AGE_MULT) * _bar_interval_seconds() + float(STALE_BAR_GRACE_SECONDS)
    return age_seconds > max_age, age_seconds


def _is_market_open_now(yf_symbol: str, now_utc: pd.Timestamp | None = None) -> bool:
    """
    Coarse session gate for minimizing free-feed calls.
    - US equities: 04:00-20:00 America/New_York (extended hours)
    - EU equities (.AS, .DE): 08:00-18:00 local exchange timezone (broad extended window)
    Weekends are always closed.
    """
    now = now_utc if now_utc is not None else pd.Timestamp.now(tz=_UTC)
    if now.tzinfo is None:
        now = now.tz_localize(_UTC)
    if now.weekday() >= 5:
        return False

    sym = str(yf_symbol or "").upper()
    if sym.endswith(".AS"):
        local = now.tz_convert(_AMS_TZ)
        t = local.time()
        return _EU_EXT_OPEN <= t < _EU_EXT_CLOSE
    if sym.endswith(".DE"):
        local = now.tz_convert(_BERLIN_TZ)
        t = local.time()
        return _EU_EXT_OPEN <= t < _EU_EXT_CLOSE

    local = now.tz_convert(_NY_TZ)
    t = local.time()
    return _US_EXT_OPEN <= t < _US_EXT_CLOSE


async def fetch_5m_bars(symbol: str, lookback_bars: int = LOOKBACK_BARS) -> tuple[pd.DataFrame, bool]:
    # yfinance is synchronous, so run it in a thread.
    def _download() -> pd.DataFrame:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return yf.download(
                tickers=symbol,
                period="10d",
                interval="5m",
                auto_adjust=False,
                progress=False,
                threads=False,
            )

    def _history_fallback() -> pd.DataFrame:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return yf.Ticker(symbol).history(period="10d", interval="5m", auto_adjust=False)

    raw = pd.DataFrame()
    # History endpoint is usually more stable for single-ticker polling.
    for attempt in range(3):
        try:
            raw = await asyncio.to_thread(_history_fallback)
            if not raw.empty:
                break
        except Exception:
            pass
        await asyncio.sleep(0.5 * (2**attempt))

    if raw.empty:
        # Secondary fallback to download() for compatibility.
        for attempt in range(2):
            try:
                raw = await asyncio.to_thread(_download)
                if not raw.empty:
                    break
            except Exception:
                pass
            await asyncio.sleep(0.5 * (2**attempt))

    if raw.empty:
        cached = _LAST_GOOD_BARS.get(symbol)
        if cached is not None and not cached.empty:
            return cached.tail(lookback_bars).copy(), True
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"]), False
    raw = _flatten_yf_columns(raw)
    bars = _normalize_ohlcv_columns(raw)
    if bars.empty:
        cached = _LAST_GOOD_BARS.get(symbol)
        if cached is not None and not cached.empty:
            return cached.tail(lookback_bars).copy(), True
        return bars, False
    out = bars.tail(lookback_bars).copy()
    _LAST_GOOD_BARS[symbol] = out
    return out, False


def _is_time_filter_blocked(timestamp: pd.Timestamp) -> bool:
    if not ENABLE_TIME_FILTER:
        return False
    # Convert to US market timezone before applying the lunch-hour entry filter.
    ts = timestamp.tz_localize("UTC") if timestamp.tzinfo is None else timestamp
    ts_ny = ts.tz_convert(_NY_TZ)
    t = ts_ny.time()
    return _LUNCH_START <= t < _LUNCH_END


def _build_signal_snapshot(df: pd.DataFrame) -> dict[str, Any]:
    if len(df) < 2:
        return {"ready": False, "reason": "not_enough_bars"}

    row = df.iloc[-1]
    prev = df.iloc[-2]
    needed = [
        row["atr_5m"],
        row["fast_5m"],
        row["slow_5m"],
        row["fast_15m"],
        row["slow_15m"],
        row["ema_15m"],
        row["atr_15m"],
        prev["fast_5m"],
        prev["slow_5m"],
        prev["fast_15m"],
        prev["slow_15m"],
    ]
    indicators_ready = bool(np.isfinite(needed).all())
    if not indicators_ready:
        return {"ready": False, "reason": "indicators_not_ready"}

    regime_long = (
        row["close"] > row["ema_15m"] and row["fast_15m"] > row["slow_15m"] and row["fast_15m"] < 75
    )
    regime_short = (
        row["close"] < row["ema_15m"] and row["fast_15m"] < row["slow_15m"] and row["fast_15m"] > 25
    )
    long_trigger = (
        cross_up(prev["fast_5m"], prev["slow_5m"], row["fast_5m"], row["slow_5m"]) and row["fast_5m"] < 75
    )
    short_trigger = (
        cross_down(prev["fast_5m"], prev["slow_5m"], row["fast_5m"], row["slow_5m"]) and row["fast_5m"] > 25
    )

    regime = "long" if regime_long else "short" if regime_short else "none"
    trigger = "long" if long_trigger else "short" if short_trigger else "none"
    signal_side = regime if regime == trigger and regime != "none" else "none"
    time_filter_blocked = _is_time_filter_blocked(df.index[-1])
    if time_filter_blocked:
        signal_side = "none"

    return {
        "ready": True,
        "timestamp": str(df.index[-1]),
        "regime": regime,
        "trigger": trigger,
        "signal_side": signal_side,
        "signal_high": float(row["high"]),
        "signal_low": float(row["low"]),
        "close": float(row["close"]),
        "atr_5m": float(row["atr_5m"]),
        "fast_5m": float(row["fast_5m"]),
        "slow_5m": float(row["slow_5m"]),
        "fast_15m": float(row["fast_15m"]),
        "slow_15m": float(row["slow_15m"]),
        "ema_15m": float(row["ema_15m"]),
        "atr_15m": float(row["atr_15m"]),
        "prev_fast_15m": float(prev["fast_15m"]) if pd.notna(prev["fast_15m"]) else None,
        "prev_slow_15m": float(prev["slow_15m"]) if pd.notna(prev["slow_15m"]) else None,
        "prev_ema_15m": float(prev["ema_15m"]) if pd.notna(prev["ema_15m"]) else None,
        "time_filter_blocked": time_filter_blocked,
    }


async def get_latest_signals() -> dict[str, dict[str, Any]]:
    signals: dict[str, dict[str, Any]] = {}
    live_fetches_used = 0
    for yf_symbol, t212_symbol in SYMBOLS_MAP.items():
        try:
            now_utc = pd.Timestamp.now(tz=_UTC)
            next_retry = _NEXT_RETRY_UTC.get(yf_symbol)
            if next_retry is not None and now_utc < next_retry:
                remaining = float((next_retry - now_utc).total_seconds())
                signals[yf_symbol] = {
                    "ready": False,
                    "reason": f"data_backoff:{remaining:.1f}s",
                    "t212_ticker": t212_symbol,
                    "market_open": True,
                }
                continue
            market_open = _is_market_open_now(yf_symbol, now_utc=now_utc)
            used_cached_data = False
            if market_open:
                # Hard ceiling: cap live fetches per cycle to avoid provider throttling.
                if int(MAX_LIVE_FETCHES_PER_CYCLE) <= 0 or live_fetches_used >= int(
                    MAX_LIVE_FETCHES_PER_CYCLE
                ):
                    cached = _LAST_GOOD_BARS.get(yf_symbol)
                    if cached is not None and not cached.empty:
                        bars_5m = cached.tail(LOOKBACK_BARS).copy()
                        used_cached_data = True
                    else:
                        bars_5m = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
                        used_cached_data = True
                else:
                    # Stagger requests so we don't burst-hit rate limits.
                    stagger = max(float(FETCH_STAGGER_SECONDS), 0.0)
                    if stagger > 0:
                        await asyncio.sleep(stagger + random.uniform(0.0, min(0.25, stagger)))
                    bars_5m, used_cached_data = await fetch_5m_bars(yf_symbol)
                    live_fetches_used += 1
            else:
                # Do not burn API calls when exchange is closed; use cached bars for management only.
                cached = _LAST_GOOD_BARS.get(yf_symbol)
                if cached is not None and not cached.empty:
                    bars_5m = cached.tail(LOOKBACK_BARS).copy()
                    used_cached_data = True
                else:
                    bars_5m = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
            if bars_5m.empty:
                # Treat empty payloads as a transient provider failure and apply per-symbol backoff.
                # This prevents hammering yfinance when it returns empty frames during hiccups.
                if market_open:
                    streak = int(_NO_DATA_STREAK.get(yf_symbol, 0)) + 1
                    _NO_DATA_STREAK[yf_symbol] = streak
                    backoff_seconds = min(120.0, float(2**min(streak, 6)))
                    _NEXT_RETRY_UTC[yf_symbol] = now_utc + pd.Timedelta(seconds=backoff_seconds)
                else:
                    _NO_DATA_STREAK[yf_symbol] = 0
                signals[yf_symbol] = {
                    "ready": False,
                    "reason": (
                        "no_data"
                        if not market_open
                        else f"no_data_backoff:{float(backoff_seconds):.0f}s"
                    )
                    if market_open
                    else (
                        # Include UTC + NY time to make "is it really premarket?" debugging obvious.
                        f"market_closed_no_cache(now_utc={now_utc.isoformat()}, "
                        f"ny={now_utc.tz_convert(_NY_TZ).isoformat()})"
                    ),
                    "t212_ticker": t212_symbol,
                    "market_open": market_open,
                    "live_fetches_used": live_fetches_used,
                }
                continue
            _NO_DATA_STREAK[yf_symbol] = 0

            # Freshness gate: even when yfinance returns data successfully, the newest bar can be
            # hours/days old (e.g. premarket / API lag). Block candle-driven signals in that case.
            last_bar_ts = pd.Timestamp(bars_5m.index[-1])
            stale_by_ts, age_seconds = _is_stale_last_bar(last_bar_ts, yf_symbol=yf_symbol)
            # If this symbol was paused due to repeated staleness, keep it paused until it becomes fresh.
            if yf_symbol in _PAUSED_FOR_STALE and not stale_by_ts:
                _PAUSED_FOR_STALE.discard(yf_symbol)
                _STALE_STRIKES[yf_symbol] = 0

            with_indicators = add_indicators(bars_5m, ema_period=EMA_PERIOD)
            snapshot = _build_signal_snapshot(with_indicators)
            snapshot["t212_ticker"] = t212_symbol
            snapshot["bars"] = with_indicators
            snapshot["bar_ts"] = str(_to_utc_timestamp(_localize_bar_timestamp(last_bar_ts, yf_symbol=yf_symbol)).isoformat())
            snapshot["bar_age_seconds"] = float(age_seconds)
            snapshot["market_open"] = market_open
            snapshot["live_fetches_used"] = live_fetches_used
            # Entry gating flag: we still want active-position management to run, even if entries are blocked.
            snapshot["entry_blocked"] = False

            if not market_open:
                # Market closed: allow manager to run, but block new entries by forcing signal_side none.
                snapshot["signal_side"] = "none"
                snapshot["time_filter_blocked"] = True
                snapshot["reason"] = "market_closed"
                snapshot["entry_blocked"] = True
            elif used_cached_data or stale_by_ts:
                # Data freshness failure: keep snapshot usable for management, but block entries.
                snapshot["signal_side"] = "none"
                snapshot["reason"] = "stale_data"
                snapshot["entry_blocked"] = True
            signals[yf_symbol] = snapshot

            # Update stale strikes/pause state after snapshot creation.
            if market_open and snapshot.get("reason") == "stale_data":
                strikes = int(_STALE_STRIKES.get(yf_symbol, 0)) + 1
                _STALE_STRIKES[yf_symbol] = strikes
                snapshot["stale_strikes"] = strikes
                if strikes >= int(STALE_BAR_STRIKES_TO_PAUSE):
                    _PAUSED_FOR_STALE.add(yf_symbol)
            else:
                _STALE_STRIKES[yf_symbol] = 0
                snapshot["stale_strikes"] = 0

            # If paused, enforce manage-only behavior even if yfinance returns something.
            if yf_symbol in _PAUSED_FOR_STALE:
                # Only keep "paused_stale" during expected session; outside hours it's just market_closed.
                if market_open:
                    snapshot["reason"] = "paused_stale"
                    snapshot["signal_side"] = "none"
                    snapshot["entry_blocked"] = True
                    signals[yf_symbol] = snapshot

            # Success: clear fetch failure backoff.
            _FAIL_STREAK[yf_symbol] = 0
            _NEXT_RETRY_UTC.pop(yf_symbol, None)
        except Exception as exc:
            streak = int(_FAIL_STREAK.get(yf_symbol, 0)) + 1
            _FAIL_STREAK[yf_symbol] = streak
            # Backoff grows up to ~2 minutes, per symbol.
            backoff_seconds = min(120.0, float(2**min(streak, 6)))
            _NEXT_RETRY_UTC[yf_symbol] = pd.Timestamp.now(tz=_UTC) + pd.Timedelta(
                seconds=backoff_seconds
            )
            signals[yf_symbol] = {
                "ready": False,
                "reason": f"data_error: {exc}",
                "t212_ticker": t212_symbol,
                "market_open": True,
                "backoff_seconds": backoff_seconds,
            }
    return signals
