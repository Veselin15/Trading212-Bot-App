"""
Live Paper-Trading Engine  –  t212_miner_bot
===============================================

Translates the walk-forward backtest logic into a real-time loop.

The runtime scheduler wakes up every 5 minutes (for responsiveness), but
**entries are only evaluated on fresh 15-minute candle closes** to preserve
the exact production signal semantics.

Architecture
------------
  1. Startup
     - Load all 25 trained ML models
     - Connect to T212 (demo by default; set T212_BASE_URL for live)
     - Auto-resolve Yahoo Finance symbols → T212 tickers
     - Sync open positions from broker
     - Load persisted state from live_state.json

  2. Main loop  (every 5 minutes; entries gated to 15m closes)
     a. Fetch 15m + 5m OHLCV bars via yfinance (last 30 days → warm-up)
     b. Compute all features (same pipeline as backtest)
     c. Run ML inference → confidence scores per symbol
     d. Compute macro regime fraction (>50% of universe above EMA200 → bull)
     e. Process exits for every open position:
            - Take-profit hit?
            - ATR trailing stop triggered?
            - Hard stop-loss hit?
            - Max holding bars exceeded?
        → Market sell order + remove from state
     f. Generate new BUY signals:
            - Apply sector clamping
            - Apply dynamic macro risk scale
            - Apply cash / exposure limits
        → Market buy order + add to state
     g. Persist state + write cycle log

  3. Notifications
     - Telegram message on every entry / exit (optional, requires BOT_TOKEN + CHAT_ID)
     - Log file in logs/live_trader.log

Configuration  (env vars)
-------------------------
  T212_API_KEY            Required.  Your T212 API token.
  T212_BASE_URL           Default: https://demo.trading212.com
  TELEGRAM_BOT_TOKEN      Optional.  Enables Telegram alerts.
  TELEGRAM_CHAT_ID        Optional.

Run
---
  # Paper trading (demo account):
  python -m t212_miner_bot.live_trader

  # Dry run (computes signals but places NO orders):
  python -m t212_miner_bot.live_trader --dry-run

  # One cycle immediately then exit (for testing):
  python -m t212_miner_bot.live_trader --once
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf

from t212_miner_bot.twelvedata_live import fetch_intraday as twelvedata_fetch_intraday

from t212_miner_bot.config import (
    EU_SYMBOLS,
    INITIAL_CAPITAL,
    SYMBOL_THRESHOLDS,
    EXEC_TP_ATR_MULT,
    EXEC_SL_ATR_MULT,
    ATR_TRAIL_MULT,
    ATR_TRAIL_ACTIVATE_R,
    REQUIRE_TREND_UP,
    MIN_ADX_FOR_ENTRY,
    COOLDOWN_BARS_AFTER_TRADE,
    SESSION_FILTER_ENABLED,
    SESSION_CLOSE_BLOCK_UTC_HOUR,
    SESSION_CLOSE_BLOCK_UTC_MINUTE,
    MAX_TOTAL_EXPOSURE_PCT,
    MAX_OPEN_POSITIONS,
    PYRAMID_ATR_MULT,
    PYRAMID_FRACTION,
    PYRAMID_SYMBOLS,
    SECTOR_CLAMPING_ENABLED,
    SYMBOL_SECTOR,
    DYNAMIC_MACRO_RISK_ENABLED,
    MACRO_REGIME_BULL_THRESHOLD,
    MACRO_BULL_RISK_SCALE,
    MACRO_BEAR_RISK_SCALE,
    SYMBOL_RISK_PCT,
    SYMBOL_MAX_POSITION_PCT,
    RISK_PER_TRADE_PCT,
    KELLY_MAX_MULT,
    KELLY_CONFIDENCE_CEIL,
    MAX_POSITION_PCT,
)
from t212_miner_bot.features import (
    compute_all_features,
    get_feature_columns,
    compute_sector_relative_strength,
    attach_sector_rs,
)
from t212_miner_bot.ensemble_model import EnsembleModel
from t212_miner_bot.strategy import SwingStrategy
from t212_miner_bot.production import (
    build_strategy,
    PRODUCTION_BLOCKLIST,
    PROD_BULL, PROD_BEAR, PROD_SLOTS, PROD_EXPOSURE,
    PROD_POS_CEILING, PROD_RISK_CEILING,
)
from t212_miner_bot.position_sizing import (
    adjust_for_available_cash,
    calculate_position_size,
    check_portfolio_limits,
)
from t212_miner_bot.t212_client import T212Client
from t212_miner_bot.ticker_resolver import TickerResolver
from t212_miner_bot.trade_audit import audit

# ── Logging ───────────────────────────────────────────────────────────────────

LOG_DIR  = Path(__file__).resolve().parents[1] / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "live_trader.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

# ── Terminal colors (ANSI) ────────────────────────────────────────────────────
# Works in most modern terminals. On Windows, enabling VT mode is usually handled
# by the terminal host; we also fall back gracefully if ANSI isn't supported.

_COLOR = os.getenv("BOT_COLORS", "1").strip() not in ("0", "false", "False", "")

def _c(code: str, text: str) -> str:
    if not _COLOR:
        return text
    return f"\x1b[{code}m{text}\x1b[0m"

def c_info(s: str) -> str:   return _c("36", s)   # cyan
def c_ok(s: str) -> str:     return _c("32", s)   # green
def c_warn(s: str) -> str:   return _c("33", s)   # yellow
def c_err(s: str) -> str:    return _c("31", s)   # red
def c_dim(s: str) -> str:    return _c("2", s)    # dim
def c_bold(s: str) -> str:   return _c("1", s)    # bold

# ── State path ────────────────────────────────────────────────────────────────

STATE_PATH = Path(__file__).resolve().parent / "live_state.json"

# Cash / broker sync (live account safety)
CASH_RESERVE_PCT = float(os.getenv("BOT_CASH_RESERVE_PCT", "0.03"))
MIN_ORDER_EUR = float(os.getenv("BOT_MIN_ORDER_EUR", "25"))
ORDER_FAIL_COOLDOWN_CYCLES = int(os.getenv("BOT_ORDER_FAIL_COOLDOWN", "6"))
BROKER_QTY_EPS = 1e-4

# ── Per-position state ────────────────────────────────────────────────────────

@dataclass
class LivePosition:
    """Tracks a single open position in the live engine."""
    symbol:              str
    t212_ticker:         str
    entry_price:         float
    shares:              float
    entry_time:          str         # ISO-8601 UTC
    take_profit:         float
    stop_loss:           float
    entry_atr:           float
    high_since_entry:    float
    trail_stop:          float       = 0.0
    trail_active:        bool        = False
    pyramid_done:        bool        = False
    original_shares:     float       = 0.0
    bars_held:           int         = 0
    entry_confidence:    float       = 0.0
    last_exit_bar_idx:   int         = 0


@dataclass
class BrokerSnapshot:
    """Broker cash + holdings for one cycle (used for sizing and reconcile)."""
    free: float
    invested: float
    total: float
    ticker_qty: Dict[str, float]
    usable_cash: float
    is_live: bool


# ── Telegram notifier (optional) ──────────────────────────────────────────────

def _telegram(msg: str) -> None:
    token   = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": msg},
            timeout=6,
        )
    except Exception as exc:
        log.warning("Telegram notification failed: %s", exc)


# ── Timing helpers ────────────────────────────────────────────────────────────

# Scheduler heartbeat. If you only evaluate on closed 15m bars, running every
# 15 minutes is sufficient and reduces API calls. Override via env var.
_SCHEDULE_MINUTES = int(os.getenv("BOT_SCHEDULE_MINUTES", "5").strip() or "5")
_ENTRY_MINUTES    = 15        # entries only on new 15m closes
_SIGNAL_BUFFER    = 20        # seconds after candle close before firing
_MAX_JITTER       = 3.0       # random extra seconds to avoid hammering yfinance


def _seconds_until_next_schedule() -> float:
    """How many seconds until the next 5m tick (+ buffer + jitter)."""
    now      = datetime.now(tz=timezone.utc)
    minute   = now.minute
    second   = now.second + now.microsecond / 1e6
    # Next multiple of 5 minutes
    rem      = minute % _SCHEDULE_MINUTES
    wait_min = (_SCHEDULE_MINUTES - rem) if rem > 0 else _SCHEDULE_MINUTES
    wait_sec = wait_min * 60 - second
    return max(wait_sec + _SIGNAL_BUFFER + random.uniform(0, _MAX_JITTER), 1.0)


def _is_new_15m_close(ts_utc: datetime) -> bool:
    """True when timestamp aligns to a 15-minute boundary (minute % 15 == 0)."""
    return (ts_utc.minute % _ENTRY_MINUTES) == 0


# ── Data fetcher ──────────────────────────────────────────────────────────────

_BAR_CACHE: Dict[str, Dict[str, pd.DataFrame]] = {}   # symbol → {"15m": df, "5m": df}
_BAR_CACHE_TS: Dict[str, pd.Timestamp] = {}           # symbol → latest 15m bar timestamp cached
_FAIL_STREAK: Dict[str, int] = {}                     # symbol → consecutive fetch failures
_DISABLED: Dict[str, float] = {}                      # symbol → disabled_until_epoch (seconds)

_MAX_FAIL_STREAK = 6          # after this many failures, pause symbol for a while
_DISABLE_SECONDS = 60 * 30    # 30 minutes pause (reduces log spam)
_CACHE_MAX_AGE_S = 60 * 8     # if cache last bar is newer than this, reuse instead of refetch

# ── Network/DNS outage guard ────────────────────────────────────────────────
# When DNS resolution fails, *all* symbols and broker calls will fail and the
# bot will spam logs (25 symbols × retries). Detect this and back off globally.

_NET_DOWN_UNTIL: float = 0.0
_NET_LAST_LOG: float = 0.0
_NET_BACKOFF_S: float = 60 * 5   # 5 minutes
_NET_LOG_THROTTLE_S: float = 30.0

def _looks_like_dns_failure(exc: Exception) -> bool:
    s = str(exc)
    # requests/urllib3 surface this as NameResolutionError(... getaddrinfo failed)
    return ("NameResolutionError" in s) or ("getaddrinfo failed" in s) or ("Failed to resolve" in s)

def _note_network_down(exc: Exception, where: str) -> None:
    global _NET_DOWN_UNTIL, _NET_LAST_LOG
    now = time.time()
    _NET_DOWN_UNTIL = max(_NET_DOWN_UNTIL, now + _NET_BACKOFF_S)
    # log at most once every _NET_LOG_THROTTLE_S seconds
    if now - _NET_LAST_LOG >= _NET_LOG_THROTTLE_S:
        _NET_LAST_LOG = now
        log.warning(c_warn(f"[network] DNS/network issue detected in {where}; pausing live fetches for {_NET_BACKOFF_S//60:.0f}m: {exc}"))

# Some Yahoo Finance symbols return empty intraday data with the exchange suffix.
# Map these to alternative tickers that yfinance resolves correctly.
_YFINANCE_ALIAS: Dict[str, list[str]] = {
    # Some tickers are flaky on intraday. Try a sequence of aliases.
    "ROG.SW":  ["ROG", "ROG.SW"],  # try base ticker first to avoid noisy Yahoo errors
    "ENR.DE":  ["ENR.DE"],
}

def _fetch_bars(symbol: str, retries: int = 3) -> Optional[Dict[str, pd.DataFrame]]:
    """
    Fetch 30 days of 15m and 5m bars for one symbol via yfinance.
    Returns {"15m": df, "5m": df} or None on failure.
    """
    # If symbol is temporarily disabled due to repeated failures, use cache if available.
    now_epoch = time.time()

    # Global network outage: immediately fall back to cache (or None)
    if _NET_DOWN_UNTIL > now_epoch:
        if symbol in _BAR_CACHE:
            return _BAR_CACHE[symbol]
        return None

    disabled_until = _DISABLED.get(symbol, 0.0)
    if disabled_until > now_epoch:
        if symbol in _BAR_CACHE:
            return _BAR_CACHE[symbol]
        return None

    # Use cache if it's fresh enough (reduces yfinance flakiness)
    if symbol in _BAR_CACHE_TS:
        age = now_epoch - float(_BAR_CACHE_TS[symbol].timestamp())
        if age <= _CACHE_MAX_AGE_S and symbol in _BAR_CACHE:
            return _BAR_CACHE[symbol]

    aliases = _YFINANCE_ALIAS.get(symbol, [symbol])

    for attempt in range(retries):
        try:
            fetch_sym = aliases[min(attempt, len(aliases) - 1)]
            tkr   = yf.Ticker(fetch_sym)
            df15  = tkr.history(period="30d", interval="15m", auto_adjust=False)
            df5   = tkr.history(period="7d",  interval="5m",  auto_adjust=False)

            # yfinance can return None or non-DataFrame in rare cases
            if df15 is None or not isinstance(df15, pd.DataFrame):
                df15 = pd.DataFrame()
            if df5 is None or not isinstance(df5, pd.DataFrame):
                df5 = pd.DataFrame()
            if df15.empty:
                raise ValueError("empty 15m bars")
            # Normalise column names to lowercase
            df15.columns = [c.lower() for c in df15.columns]
            if not df5.empty:
                df5.columns  = [c.lower() for c in df5.columns]
            # Ensure UTC-aware index
            for df in (df15, df5):
                if df is None or df.empty:
                    continue
                if df.index.tzinfo is None:
                    df.index = df.index.tz_localize("UTC")
                else:
                    df.index = df.index.tz_convert("UTC")
            result = {"15m": df15, "5m": df5 if not df5.empty else None}
            _BAR_CACHE[symbol] = result
            _BAR_CACHE_TS[symbol] = pd.Timestamp(df15.index[-1]).tz_convert("UTC")
            _FAIL_STREAK[symbol] = 0
            return result
        except Exception as exc:
            if _looks_like_dns_failure(exc):
                _note_network_down(exc, where=f"yfinance({_YFINANCE_ALIAS.get(symbol, [symbol])[0]})")
                break
            _FAIL_STREAK[symbol] = _FAIL_STREAK.get(symbol, 0) + 1
            # Only warn on first failure in a streak to reduce spam
            if _FAIL_STREAK[symbol] in (1, 3):
                log.warning(c_warn(f"  [{symbol}] yfinance failed (streak {_FAIL_STREAK[symbol]}): {exc}"))
            if attempt < retries - 1:
                time.sleep(1.5 * (2 ** attempt))

    # ── TwelveData fallback (only if configured) ─────────────────────────
    # Trading212 API does not provide candle history, only positions/prices,
    # so our free fallback option is a real market-data provider.
    try:
        df15_td = twelvedata_fetch_intraday(symbol, interval_min=15)
        if df15_td is not None and not df15_td.empty:
            df5_td = twelvedata_fetch_intraday(symbol, interval_min=5)
            result = {"15m": df15_td, "5m": df5_td if df5_td is not None and not df5_td.empty else None}
            _BAR_CACHE[symbol] = result
            _BAR_CACHE_TS[symbol] = pd.Timestamp(df15_td.index[-1]).tz_convert("UTC")
            _FAIL_STREAK[symbol] = 0
            log.warning(c_warn(f"  [{symbol}] using TwelveData fallback for intraday bars"))
            return result
        # If TwelveData is configured but has no data for this symbol, be explicit once.
        # (This commonly happens for some venues on free plans.)
        if df15_td is None or df15_td.empty:
            if _FAIL_STREAK.get(symbol, 0) in (1, 3):
                log.warning(c_warn(f"  [{symbol}] TwelveData returned no intraday data (fallback unavailable)"))
    except Exception as exc:
        if _looks_like_dns_failure(exc):
            _note_network_down(exc, where="TwelveData")
        # Fall through to cache/disable logic
        log.warning(c_warn(f"  [{symbol}] TwelveData fallback failed: {exc}"))

    # Fallback to cache
    if symbol in _BAR_CACHE:
        if _FAIL_STREAK.get(symbol, 0) >= _MAX_FAIL_STREAK:
            _DISABLED[symbol] = time.time() + _DISABLE_SECONDS
            log.warning(c_warn(f"  [{symbol}] disabled for {_DISABLE_SECONDS//60}m (repeated yfinance failures)"))
        log.warning(c_warn(f"  [{symbol}] using cached bars (live fetch failed)"))
        return _BAR_CACHE[symbol]
    if _FAIL_STREAK.get(symbol, 0) >= _MAX_FAIL_STREAK:
        _DISABLED[symbol] = time.time() + _DISABLE_SECONDS
        log.warning(c_warn(f"  [{symbol}] disabled for {_DISABLE_SECONDS//60}m (repeated yfinance failures)"))
    return None


# ── Main engine ───────────────────────────────────────────────────────────────

class LiveTrader:
    """
    End-to-end live/paper trading engine.

    Parameters
    ----------
    dry_run : bool
        When True, signals are computed but no orders are sent to T212.
        Useful for testing the pipeline without risking paper capital.
    """

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run  = dry_run
        # Production "BEST_SAFE" strategy: SwingStrategyV3 with trend-scaled
        # take-profit + breakout-tight stops (see production.build_strategy).
        self.strategy = build_strategy()

        self.models: Dict[str, EnsembleModel]  = {}
        self.positions: Dict[str, LivePosition] = {}
        self.last_exit_bar: Dict[str, int]      = {}
        self.last_exit_was_win: Dict[str, bool] = {}
        self.bar_counter: int                   = 0

        self.client:   Optional[T212Client]    = None
        self.resolver: Optional[TickerResolver] = None
        self.ticker_map: Dict[str, str]         = {}

        # Last known broker equity (so transient API issues don't revert sizing to INITIAL_CAPITAL)
        self._last_equity: float = INITIAL_CAPITAL
        self._last_equity_ts: float = 0.0
        self._last_free_cash: float = 0.0
        self._last_cash: Optional[dict] = None
        self._cycle_num: int = 0
        self._buy_fail_cycle: Dict[str, int] = {}

    # ── Startup ──────────────────────────────────────────────────────────

    def startup(self) -> None:
        log.info("=" * 70)
        log.info("  t212_miner_bot  –  Live Trader  (%s)",
                 "DRY RUN" if self.dry_run else "PAPER TRADING")
        log.info("  Base URL : %s", os.getenv("T212_BASE_URL", "https://demo.trading212.com"))
        log.info("=" * 70)

        self._load_models()
        self._load_state()

        self.client   = T212Client()
        self.resolver = TickerResolver(self.client)
        self.resolver.build()

        from t212_miner_bot.config import EU_SYMBOLS as _SYMS
        available = [s for s in _SYMS
                     if s not in PRODUCTION_BLOCKLIST and EnsembleModel._model_path(s).exists()]
        self.ticker_map = self.resolver.resolve_all(available)

        # Verify connection + log equity
        try:
            cash_data = self.client.get_cash()
            log.info("  Account cash: free=%.2f  invested=%.2f  total=%.2f",
                     cash_data.get("free", 0),
                     cash_data.get("invested", 0),
                     cash_data.get("total", 0))
            self._last_cash = cash_data
            total = float(cash_data.get("total", INITIAL_CAPITAL))
            free  = float(cash_data.get("free", 0))
            self._sync_broker_at_cycle_start(total, free, is_live=True)
            self._import_broker_positions_into_state()
        except Exception as exc:
            log.error("  T212 connection failed: %s", exc)
            if not self.dry_run:
                raise

        log.info("  Models loaded   : %d / %d", len(self.models), len(available))
        log.info("  Ticker resolved : %d", len(self.ticker_map))
        log.info("  Open positions  : %d (from state)", len(self.positions))
        if audit.enabled:
            log.info("  Audit log       : %s", audit.jsonl_path)
            log.info("  Trade ledger    : %s", audit.trades_csv_path)
        log.info("=" * 70)

    def _import_broker_positions_into_state(self) -> None:
        """
        Ensure state reflects broker reality.

        If the broker reports an open position for a ticker belonging to our
        universe but `live_state.json` doesn't include it, import it with
        reasonable TP/SL computed from current ATR.
        """
        # Even in dry-run we still want state to reflect broker positions.
        if not self.client:
            return

        try:
            portfolio = self.client.get_portfolio()
        except Exception as exc:
            log.warning("  Broker import skipped (portfolio fetch failed): %s", exc)
            return

        # Reverse map: T212 ticker → Yahoo symbol
        t212_to_symbol = {t212: sym for sym, t212 in self.ticker_map.items()}

        imported: List[str] = []
        for p in portfolio:
            t = p.get("ticker")
            qty = p.get("quantity") if p.get("quantity") is not None else p.get("currentQuantity")
            avg = p.get("averagePrice") if p.get("averagePrice") is not None else p.get("averagePricePaid")
            if t is None or qty is None or avg is None:
                continue

            t = str(t)
            sym = t212_to_symbol.get(t)
            if sym is None:
                continue  # not part of our universe
            if sym in self.positions:
                continue  # already tracked

            try:
                qty_f = float(qty)
                avg_f = float(avg)
            except Exception:
                continue
            if qty_f <= 0:
                continue

            # Compute current ATR from latest bars so we can reconstruct TP/SL.
            bars = _fetch_bars(sym)
            atr = 0.0
            high_since = avg_f
            if bars and isinstance(bars.get("15m"), pd.DataFrame) and not bars["15m"].empty:
                df = bars["15m"].copy()
                try:
                    compute_all_features(df, bars.get("5m"), symbol=sym)
                    last_atr = float(df.get("atr", pd.Series([0.0])).iloc[-1])
                    atr = last_atr if last_atr > 0 else 0.0
                    high_since = max(avg_f, float(df["high"].iloc[-1]))
                except Exception:
                    atr = 0.0

            if atr <= 0:
                log.warning("  Import skipped for %s (%s): could not compute ATR from live bars", sym, t)
                continue

            tp = avg_f + EXEC_TP_ATR_MULT * atr
            sl = avg_f - EXEC_SL_ATR_MULT * atr

            self.positions[sym] = LivePosition(
                symbol=sym,
                t212_ticker=t,
                entry_price=avg_f,
                shares=qty_f,
                entry_time=datetime.now(tz=timezone.utc).isoformat(),
                take_profit=tp,
                stop_loss=sl,
                entry_atr=atr,
                high_since_entry=high_since,
                trail_stop=0.0,
                trail_active=False,
                pyramid_done=True,     # conservative: don't pyramid into imported/manual positions
                original_shares=qty_f,
                bars_held=0,
                entry_confidence=0.0,
            )
            imported.append(sym)

        if imported:
            log.warning("  Imported broker positions into state: %s", imported)
            audit.log_reconcile(removed_symbols=[], imported_symbols=imported)

    def _portfolio_ticker_qty(self) -> Dict[str, float]:
        """Map T212 ticker → quantity from broker portfolio."""
        if self.dry_run or not self.client:
            return {}
        try:
            portfolio = self.client.get_portfolio()
        except Exception as exc:
            log.warning("  Portfolio fetch failed: %s", exc)
            return {}

        ticker_qty: Dict[str, float] = {}
        for p in portfolio:
            t = p.get("ticker")
            q = (
                p.get("quantity")
                if p.get("quantity") is not None
                else p.get("currentQuantity")
            )
            if t is None or q is None:
                continue
            try:
                ticker_qty[str(t)] = float(q)
            except Exception:
                continue
        return ticker_qty

    def _sync_broker_at_cycle_start(
        self,
        equity: float,
        free_cash: float,
        is_live: bool,
    ) -> BrokerSnapshot:
        """Fetch broker holdings, reconcile state, return cash snapshot for sizing."""
        invested_est = sum(p.shares * p.entry_price for p in self.positions.values())

        if self.dry_run or not self.client or not is_live:
            usable = free_cash if free_cash > 0 else max(0.0, equity - invested_est)
            return BrokerSnapshot(
                free=free_cash,
                invested=invested_est,
                total=equity,
                ticker_qty={},
                usable_cash=usable,
                is_live=False,
            )

        cash = self._last_cash or {}
        try:
            invested = float(cash.get("invested", invested_est))
        except Exception:
            invested = invested_est
        try:
            free = float(cash.get("free", free_cash))
        except Exception:
            free = free_cash
        try:
            total = float(cash.get("total", equity))
        except Exception:
            total = equity

        ticker_qty = self._portfolio_ticker_qty()
        usable = max(0.0, free * (1.0 - CASH_RESERVE_PCT))
        snap = BrokerSnapshot(
            free=free,
            invested=invested,
            total=total,
            ticker_qty=ticker_qty,
            usable_cash=usable,
            is_live=True,
        )
        self._reconcile_state_with_broker(snap)
        return snap

    def _reconcile_state_with_broker(self, snapshot: BrokerSnapshot) -> None:
        """Drop phantom positions and align share counts with broker holdings."""
        if self.dry_run or not snapshot.is_live:
            return

        removed: List[str] = []
        synced: List[str] = []
        ticker_qty = snapshot.ticker_qty

        for sym, pos in list(self.positions.items()):
            q = float(ticker_qty.get(pos.t212_ticker, 0.0))
            if q <= BROKER_QTY_EPS:
                removed.append(sym)
                del self.positions[sym]
                continue
            if abs(q - pos.shares) > max(BROKER_QTY_EPS, pos.shares * 0.02):
                log.warning(
                    "  Reconcile: %s shares %.4f (state) → %.4f (broker)",
                    sym, pos.shares, q,
                )
                pos.shares = q
                if pos.original_shares > q:
                    pos.original_shares = q
                synced.append(sym)

        if removed:
            log.warning("  Reconciled state: removed phantom positions %s", removed)
            audit.log_reconcile(removed_symbols=removed, imported_symbols=[])
        if synced:
            audit.log("position_qty_synced", symbols=synced, cycle=self._cycle_num)

    def _broker_qty(self, sym: str, snapshot: BrokerSnapshot) -> float:
        pos = self.positions.get(sym)
        if pos is None:
            return 0.0
        if not snapshot.is_live:
            return pos.shares
        return float(snapshot.ticker_qty.get(pos.t212_ticker, 0.0))

    def _load_models(self) -> None:
        loaded = 0
        # Skip chronic-loser blocklist (validation-derived; see production.py)
        universe = [s for s in EU_SYMBOLS if s not in PRODUCTION_BLOCKLIST]
        for sym in universe:
            try:
                self.models[sym] = EnsembleModel.load(sym)
                loaded += 1
            except Exception:
                pass
        log.info("Loaded %d / %d ML models (blocklist excluded: %s)",
                 loaded, len(universe), sorted(PRODUCTION_BLOCKLIST))

    def _load_state(self) -> None:
        if STATE_PATH.exists():
            try:
                raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
                for sym, d in raw.get("positions", {}).items():
                    self.positions[sym] = LivePosition(**d)
                self.last_exit_bar     = raw.get("last_exit_bar", {})
                self.last_exit_was_win = raw.get("last_exit_was_win", {})
                self.bar_counter       = raw.get("bar_counter", 0)
                log.info("State loaded from %s  (%d positions)", STATE_PATH, len(self.positions))
            except Exception as exc:
                log.warning("Could not load state (%s) – starting fresh", exc)
        else:
            log.info("No state file found – starting fresh")

    def _save_state(self) -> None:
        state = {
            "saved_at":         datetime.now(tz=timezone.utc).isoformat(),
            "bar_counter":      self.bar_counter,
            "positions":        {sym: asdict(pos) for sym, pos in self.positions.items()},
            "last_exit_bar":    self.last_exit_bar,
            "last_exit_was_win": self.last_exit_was_win,
        }

        def _to_jsonable(x):
            # Make state saving "never fail" even if a numpy/pandas scalar sneaks in.
            if isinstance(x, dict):
                return {str(k): _to_jsonable(v) for k, v in x.items()}
            if isinstance(x, (list, tuple)):
                return [_to_jsonable(v) for v in x]
            if isinstance(x, (str, int, float)) or x is None:
                return x
            if isinstance(x, bool):
                return bool(x)
            # numpy / pandas scalars often have .item()
            item = getattr(x, "item", None)
            if callable(item):
                try:
                    return _to_jsonable(item())
                except Exception:
                    pass
            return str(x)

        try:
            STATE_PATH.write_text(json.dumps(_to_jsonable(state), indent=2), encoding="utf-8")
        except Exception as exc:
            # Last resort: do not crash the bot because of state persistence.
            log.error(c_err(f"State save failed (ignored to keep bot running): {exc}"))

    # ── Main run loop ─────────────────────────────────────────────────────

    def run(self, run_once: bool = False) -> None:
        self.startup()
        cycle = 0

        while True:
            if not run_once:
                wait = _seconds_until_next_schedule()
                log.info(c_dim(f"Sleeping {wait:.0f}s until next 5m tick…"))
                try:
                    time.sleep(wait)
                except KeyboardInterrupt:
                    log.info(c_warn("KeyboardInterrupt: stopping bot gracefully (state saved)."))
                    self._save_state()
                    return

            cycle += 1
            self._cycle_num = cycle
            self.bar_counter += 1
            log.info("")
            now_utc = datetime.now(tz=timezone.utc)
            entry_tick = _is_new_15m_close(now_utc)
            tick_tag = c_ok("ENTRY") if entry_tick else c_dim("MGMT")
            log.info(c_bold(f"── CYCLE {cycle}  ({now_utc.strftime('%Y-%m-%d %H:%M')} UTC)  [{tick_tag}] ──"))

            try:
                self._run_cycle(allow_entries=entry_tick)
            except KeyboardInterrupt:
                log.info(c_warn("KeyboardInterrupt: stopping bot gracefully (state saved)."))
                self._save_state()
                return
            except Exception as exc:
                log.exception(c_err(f"Cycle {cycle} crashed: {exc} – sleeping 30s then continuing"))
                time.sleep(30)

            self._save_state()

            if run_once:
                break

    def _run_cycle(self, allow_entries: bool) -> None:
        # 1. Fetch portfolio equity from T212 and reconcile state vs broker
        equity, free_cash, equity_is_live = self._get_equity()
        snapshot = self._sync_broker_at_cycle_start(equity, free_cash, equity_is_live)
        if snapshot.is_live:
            log.info(
                "  Broker cash: free=%.2f  usable=%.2f  invested=%.2f  total=%.2f",
                snapshot.free, snapshot.usable_cash, snapshot.invested, snapshot.total,
            )

        # 2. Fetch OHLCV bars for all relevant symbols
        symbols = list(self.models.keys())
        all_15m: Dict[str, pd.DataFrame] = {}
        all_5m:  Dict[str, Optional[pd.DataFrame]] = {}

        log.info("Fetching bars for %d symbols…", len(symbols))
        for sym in symbols:
            bars = _fetch_bars(sym)
            if bars is None:
                log.warning("  [%s] no data – skipping", sym)
                continue
            all_15m[sym] = bars["15m"]
            all_5m[sym]  = bars.get("5m")
            time.sleep(0.35)   # stagger yfinance requests

        if not all_15m:
            log.warning("No bars fetched – skipping cycle")
            return

        # 3. Compute features
        log.info("Computing features…")
        sector_rs = compute_sector_relative_strength(all_15m)
        feat_data: Dict[str, pd.DataFrame] = {}
        for sym, df15 in all_15m.items():
            df = df15.copy()
            try:
                compute_all_features(df, all_5m.get(sym), symbol=sym)
                attach_sector_rs(df, sector_rs.get(sym, pd.Series(dtype=float)))
                feat_data[sym] = df
            except Exception as exc:
                log.warning("  [%s] feature computation failed: %s", sym, exc)

        # 4. ML inference – get per-bar confidence scores (use the latest bar)
        scores: Dict[str, float] = {}
        for sym, df in feat_data.items():
            model = self.models.get(sym)
            if model is None or df.empty:
                continue
            try:
                fcols = [c for c in get_feature_columns(df) if not df[c].isna().all()]
                X     = df[fcols].fillna(0.0)
                proba = model.predict_proba(X)
                scores[sym] = float(proba[-1])   # score for the latest closed bar
            except Exception as exc:
                log.warning("  [%s] inference failed: %s", sym, exc)

        # 5. Macro regime: fraction of universe above EMA200
        regime_frac = self._compute_regime_fraction(feat_data)
        is_bull      = regime_frac >= MACRO_REGIME_BULL_THRESHOLD
        eff_scale    = PROD_BULL if is_bull else PROD_BEAR
        log.info(c_info("Macro regime: ") + "%s",
                 f"{regime_frac * 100:.0f}% above EMA200 → "
                 f"{'BULL' if is_bull else 'BEAR'}  (scale={eff_scale:.1f}x)")

        # 6. Process exits for open positions (runs every 5m tick)
        self._process_exits(feat_data, equity, snapshot)

        # 7. Generate new entries (only on 15m close ticks)
        if allow_entries and equity_is_live:
            self._process_entries(feat_data, scores, equity, snapshot, eff_scale)
        else:
            if not allow_entries:
                log.info(c_dim("Entry gate: not a 15m close tick → skipping new entries this cycle"))
                audit.log_entry_skip(
                    cycle=self._cycle_num,
                    reason="not_15m_close",
                    equity=equity,
                    free_cash=free_cash,
                )
            elif not equity_is_live:
                log.warning(c_warn("Entry gate: broker equity unavailable (stale fallback) → skipping new entries this cycle"))
                audit.log_entry_skip(
                    cycle=self._cycle_num,
                    reason="equity_stale",
                    equity=equity,
                    free_cash=free_cash,
                )

        # 8. Cycle summary
        log.info("")
        log.info("── CYCLE SUMMARY ────────────────────────────────────────")
        log.info("  Open positions : %d / %d", len(self.positions), PROD_SLOTS)
        for sym, pos in self.positions.items():
            log.info("    %-14s  entry=%.2f  bars=%d  conf=%.3f",
                     sym, pos.entry_price, pos.bars_held, pos.entry_confidence)
        if not self.positions:
            log.info("    (none)")
        log.info("  Symbols scored : %d  |  Macro: %s (%.0f%% above EMA200)",
                 len(scores),
                 "BULL" if regime_frac >= MACRO_REGIME_BULL_THRESHOLD else "BEAR",
                 regime_frac * 100)

        audit.log_cycle(
            cycle=self._cycle_num,
            mode="ENTRY" if allow_entries else "MGMT",
            equity=equity,
            free_cash=free_cash,
            open_positions=len(self.positions),
            regime_frac=regime_frac,
            macro_scale=eff_scale,
            symbols_scored=len(scores),
            allow_entries=allow_entries,
            equity_is_live=equity_is_live,
        )

    # ── Equity helper ─────────────────────────────────────────────────────

    def _get_equity(self) -> tuple[float, float, bool]:
        """Return (total portfolio equity, free cash, is_live)."""
        if self.dry_run or not self.client:
            return INITIAL_CAPITAL, INITIAL_CAPITAL, False
        try:
            cash = self.client.get_cash()
            self._last_cash = cash
            total = float(cash.get("total", INITIAL_CAPITAL))
            free  = float(cash.get("free", 0))
            log.info("Portfolio equity: €%.2f  (free=%.2f)", total, free)
            self._last_equity = total
            self._last_free_cash = free
            self._last_equity_ts = time.time()
            return total, free, True
        except Exception as exc:
            if _looks_like_dns_failure(exc):
                _note_network_down(exc, where="T212 get_cash")
            log.warning("Could not fetch equity: %s – using fallback", exc)
            # Use last known equity if we have one (safer than resetting to INITIAL_CAPITAL)
            if self._last_equity_ts > 0:
                return float(self._last_equity), float(self._last_free_cash), False
            return INITIAL_CAPITAL, 0.0, False

    # ── Macro regime ──────────────────────────────────────────────────────

    def _compute_regime_fraction(self, feat_data: Dict[str, pd.DataFrame]) -> float:
        """Fraction of universe symbols whose latest close >= EMA200."""
        above = 0
        total = 0
        for sym, df in feat_data.items():
            if "ema_200" not in df.columns or df.empty:
                continue
            last_close  = float(df["close"].iloc[-1])
            last_ema200 = float(df["ema_200"].iloc[-1])
            if not np.isnan(last_ema200):
                total += 1
                if last_close >= last_ema200:
                    above += 1
        return above / total if total > 0 else 1.0

    # ── Exit processing ───────────────────────────────────────────────────

    def _process_exits(
        self,
        feat_data: Dict[str, pd.DataFrame],
        equity: float,
        snapshot: BrokerSnapshot,
    ) -> None:
        """Check every open position for exit conditions and close if triggered."""
        to_close: List[str] = []

        for sym, pos in list(self.positions.items()):
            broker_q = self._broker_qty(sym, snapshot)
            if snapshot.is_live and broker_q <= BROKER_QTY_EPS:
                log.warning(
                    "  [%s] broker has no shares – removing phantom position from state",
                    sym,
                )
                audit.log_reconcile(removed_symbols=[sym], imported_symbols=[])
                to_close.append(sym)
                continue

            df = feat_data.get(sym)
            if df is None or df.empty:
                continue

            last_bar = df.iloc[-1]
            high  = float(last_bar["high"])
            low   = float(last_bar["low"])
            close = float(last_bar["close"])

            # Update running high for trailing stop
            if high > pos.high_since_entry:
                pos.high_since_entry = high

            # Check pyramiding (add at +1.5R if not done)
            if (
                PYRAMID_SYMBOLS and sym in PYRAMID_SYMBOLS
                and not pos.pyramid_done
                and pos.entry_atr > 0
            ):
                pyr_level = pos.entry_price + PYRAMID_ATR_MULT * pos.entry_atr
                if high >= pyr_level:
                    add_shares = round(pos.original_shares * PYRAMID_FRACTION, 4)
                    add_shares = adjust_for_available_cash(
                        snapshot.usable_cash, add_shares, pyr_level,
                    )
                    pyr_cost = add_shares * pyr_level
                    if (
                        add_shares > 0
                        and pyr_cost >= MIN_ORDER_EUR
                        and pyr_cost <= snapshot.usable_cash
                    ):
                        ok = self._buy(
                            sym, add_shares, pyr_level, "pyramid_add",
                            max_cash=snapshot.usable_cash,
                        )
                        if ok:
                            pos.shares        += add_shares
                            pos.pyramid_done   = True
                            pos.stop_loss      = pos.entry_price   # move to breakeven
                            pos.trail_stop     = max(pos.trail_stop, pos.entry_price)
                            pos.trail_active   = True
                            snapshot.usable_cash = max(0.0, snapshot.usable_cash - pyr_cost)
                            log.info("  [%s] PYRAMID ADD  %.2f shares @ %.2f", sym, add_shares, pyr_level)

            pos.bars_held += 1

            # Exit check via strategy
            from t212_miner_bot.strategy import Position
            mock_pos = Position(
                symbol           = sym,
                entry_price      = pos.entry_price,
                shares           = pos.shares,
                entry_time       = datetime.fromisoformat(pos.entry_time),
                take_profit      = pos.take_profit,
                stop_loss        = pos.stop_loss,
                entry_atr        = pos.entry_atr,
                high_since_entry = pos.high_since_entry,
                trail_stop       = pos.trail_stop,
                trail_active     = pos.trail_active,
                pyramid_done     = pos.pyramid_done,
                original_shares  = pos.original_shares,
                bars_held        = pos.bars_held,
            )
            reason = self.strategy.check_exit(mock_pos, high, low, close)
            # Write back updated trail state
            pos.trail_active     = mock_pos.trail_active
            pos.trail_stop       = mock_pos.trail_stop
            pos.high_since_entry = mock_pos.high_since_entry

            if reason:
                exit_price = self.strategy.exit_price(mock_pos, reason, last_bar)
                sell_qty = min(pos.shares, broker_q) if snapshot.is_live else pos.shares
                if sell_qty <= BROKER_QTY_EPS:
                    log.warning("  [%s] EXIT skipped – no sellable quantity at broker", sym)
                    to_close.append(sym)
                    continue
                pnl = (exit_price - pos.entry_price) * sell_qty
                log.info(
                    "  [%s] EXIT  reason=%s  exit=%.4f  entry=%.4f  qty=%.4f  pnl=%+.2f EUR",
                    sym, reason, exit_price, pos.entry_price, sell_qty, pnl,
                )
                sold = self._sell(
                    sym, sell_qty, exit_price, reason, pnl_eur=pnl, broker_qty=broker_q,
                )
                if not sold:
                    log.warning("  [%s] EXIT order failed – keeping position in state", sym)
                    continue
                self.last_exit_bar[sym]     = self.bar_counter
                self.last_exit_was_win[sym] = pnl > 0
                to_close.append(sym)
                msg = (f"🔴 EXIT {sym}  {reason}  "
                       f"entry={pos.entry_price:.2f} exit={exit_price:.2f}  "
                       f"PnL={pnl:+.2f}€")
                _telegram(msg)

        for sym in to_close:
            del self.positions[sym]

    # ── Entry processing ──────────────────────────────────────────────────

    def _process_entries(
        self,
        feat_data: Dict[str, pd.DataFrame],
        scores: Dict[str, float],
        equity: float,
        snapshot: BrokerSnapshot,
        risk_scale: float,
    ) -> None:
        """Generate new BUY signals and place market orders."""
        open_syms    = set(self.positions.keys())
        open_sectors: set = set()
        if SECTOR_CLAMPING_ENABLED:
            open_sectors = {SYMBOL_SECTOR[s] for s in open_syms if s in SYMBOL_SECTOR}

        invested = (
            snapshot.invested
            if snapshot.is_live and snapshot.invested > 0
            else sum(p.shares * p.entry_price for p in self.positions.values())
        )
        cash = snapshot.usable_cash
        free_cash = snapshot.free

        # Collect candidates, sorted by confidence
        candidates: List[tuple] = []
        for sym, df in feat_data.items():
            if sym in open_syms:
                continue
            if sym not in scores:
                continue
            if sym not in self.ticker_map:
                continue
            if SECTOR_CLAMPING_ENABLED:
                sector = SYMBOL_SECTOR.get(sym)
                if sector and sector in open_sectors:
                    continue

            score       = scores[sym]
            last_bar    = df.iloc[-1]
            bars_since  = self.bar_counter - self.last_exit_bar.get(sym, -10_000)
            was_win     = self.last_exit_was_win.get(sym, True)
            threshold   = SYMBOL_THRESHOLDS.get(sym, 0.70)

            signal = self.strategy.generate_signal(
                sym, last_bar, score, open_syms,
                bars_since_last_trade=bars_since,
                threshold_override=threshold,
                last_exit_was_win=was_win,
            )
            if signal is not None:
                candidates.append((score, signal, sym))

        # Traffic-jam resolution: highest confidence first
        candidates.sort(key=lambda x: x[0], reverse=True)

        for score, signal, sym in candidates:
            if len(self.positions) >= PROD_SLOTS:
                break

            fail_at = self._buy_fail_cycle.get(sym)
            if fail_at is not None and (self._cycle_num - fail_at) < ORDER_FAIL_COOLDOWN_CYCLES:
                audit.log_signal_rejected(
                    cycle=self._cycle_num,
                    symbol=sym,
                    score=score,
                    reject_reason="order_fail_cooldown",
                    equity=equity,
                    free_cash=free_cash,
                )
                continue

            # Size the position (production "BEST_SAFE" ceilings)
            sym_risk = min(SYMBOL_RISK_PCT.get(sym, RISK_PER_TRADE_PCT) * risk_scale, PROD_RISK_CEILING)
            sym_max  = min(SYMBOL_MAX_POSITION_PCT.get(sym, MAX_POSITION_PCT) * risk_scale, PROD_POS_CEILING)

            sizing = calculate_position_size(
                portfolio_value      = equity,
                entry_price          = signal.entry_price,
                atr                  = signal.atr,
                sl_atr_mult          = self.strategy.sl_atr_mult,
                risk_pct             = sym_risk,
                confidence           = signal.confidence,
                symbol               = sym,
                symbol_max_pct_override = {sym: sym_max},
            )
            if sizing.shares <= 0:
                audit.log_signal_rejected(
                    cycle=self._cycle_num,
                    symbol=sym,
                    score=score,
                    reject_reason="zero_shares_sizing",
                    equity=equity,
                    free_cash=free_cash,
                )
                continue

            # Exposure guard (production "BEST_SAFE" exposure cap)
            total_cost = sizing.shares * signal.entry_price
            if (invested + total_cost) > equity * PROD_EXPOSURE:
                remaining = equity * PROD_EXPOSURE - invested
                if remaining < signal.entry_price:
                    continue
                sizing_shares = round(remaining / signal.entry_price, 2)
                total_cost    = sizing_shares * signal.entry_price
            else:
                sizing_shares = sizing.shares

            sizing_shares = adjust_for_available_cash(cash, sizing_shares, signal.entry_price)
            total_cost = sizing_shares * signal.entry_price

            if sizing_shares <= 0 or total_cost < MIN_ORDER_EUR:
                audit.log_signal_rejected(
                    cycle=self._cycle_num,
                    symbol=sym,
                    score=score,
                    reject_reason="below_min_order_or_zero_shares",
                    equity=equity,
                    free_cash=free_cash,
                )
                continue

            if total_cost > cash:
                audit.log_signal_rejected(
                    cycle=self._cycle_num,
                    symbol=sym,
                    score=score,
                    reject_reason="insufficient_cash",
                    equity=equity,
                    free_cash=free_cash,
                )
                continue

            if not check_portfolio_limits(
                equity, invested, len(self.positions), total_cost,
            ):
                audit.log_signal_rejected(
                    cycle=self._cycle_num,
                    symbol=sym,
                    score=score,
                    reject_reason="portfolio_limits",
                    equity=equity,
                    free_cash=free_cash,
                )
                continue

            log.info(
                "  [%s] BUY  %.2f shares @ %.4f  conf=%.3f  atr=%.4f  "
                "TP=%.4f  SL=%.4f  scale=%.1fx",
                sym, sizing_shares, signal.entry_price, score,
                signal.atr, signal.take_profit, signal.stop_loss, risk_scale,
            )
            log.info(c_ok(f"    -> ORDER: BUY {sym} {sizing_shares:.2f} shares"))
            ok = self._buy(
                sym, sizing_shares, signal.entry_price, "entry",
                max_cash=cash,
            )
            if not ok:
                continue
            self._buy_fail_cycle.pop(sym, None)

            audit.log(
                "position_opened",
                cycle=self._cycle_num,
                symbol=sym,
                shares=sizing_shares,
                entry_price=signal.entry_price,
                take_profit=signal.take_profit,
                stop_loss=signal.stop_loss,
                confidence=score,
                equity_eur=equity,
                free_cash_eur=free_cash,
            )

            self.positions[sym] = LivePosition(
                symbol           = sym,
                t212_ticker      = self.ticker_map[sym],
                entry_price      = signal.entry_price,
                shares           = sizing_shares,
                entry_time       = datetime.now(tz=timezone.utc).isoformat(),
                take_profit      = signal.take_profit,
                stop_loss        = signal.stop_loss,
                entry_atr        = signal.atr,
                high_since_entry = signal.entry_price,
                trail_stop       = 0.0,
                trail_active     = False,
                pyramid_done     = False,
                original_shares  = sizing_shares,
                bars_held        = 0,
                entry_confidence = float(score),
            )

            # Adjust tracking variables for this bar
            invested += total_cost
            cash = max(0.0, cash - total_cost)
            snapshot.usable_cash = cash
            open_syms.add(sym)
            if SECTOR_CLAMPING_ENABLED:
                sector = SYMBOL_SECTOR.get(sym)
                if sector:
                    open_sectors.add(sector)

            msg = (f"🟢 BUY {sym}  {sizing_shares:.2f} shares @ {signal.entry_price:.2f}  "
                   f"conf={score:.3f}  TP={signal.take_profit:.2f}  SL={signal.stop_loss:.2f}")
            _telegram(msg)

    # ── Order helpers ─────────────────────────────────────────────────────

    def _buy(
        self,
        sym: str,
        shares: float,
        price: float,
        reason: str,
        max_cash: Optional[float] = None,
    ) -> bool:
        if price > 0 and max_cash is not None:
            shares = adjust_for_available_cash(max_cash, shares, price)
            if shares <= 0 or shares * price < MIN_ORDER_EUR:
                log.warning(
                    "  [%s] BUY skipped (%s): notional %.2f below min or no cash (max=%.2f)",
                    sym, reason, shares * price, max_cash,
                )
                audit.log_order(
                    cycle=self._cycle_num,
                    symbol=sym,
                    side="buy",
                    shares=shares,
                    price=price,
                    reason=reason,
                    success=False,
                    error="preflight_insufficient_cash",
                    equity=self._last_equity,
                    free_cash=self._last_free_cash,
                    dry_run=self.dry_run,
                )
                if reason == "entry":
                    self._buy_fail_cycle[sym] = self._cycle_num
                return False

        ticker = self.ticker_map.get(sym)
        if not ticker:
            log.warning("  [%s] no T212 ticker – cannot place buy order", sym)
            audit.log_order(
                cycle=self._cycle_num,
                symbol=sym,
                side="buy",
                shares=shares,
                price=price,
                reason=reason,
                success=False,
                error="no_t212_ticker",
                equity=self._last_equity,
                free_cash=self._last_free_cash,
                dry_run=self.dry_run,
            )
            return False
        if self.dry_run:
            log.info("  [DRY RUN] would BUY %s  %.4f shares @ ~%.4f  (%s)", sym, shares, price, reason)
            audit.log_order(
                cycle=self._cycle_num,
                symbol=sym,
                side="buy",
                shares=shares,
                price=price,
                reason=reason,
                success=True,
                equity=self._last_equity,
                free_cash=self._last_free_cash,
                dry_run=True,
            )
            return True
        try:
            qty = round(shares, 4)
            self.client.place_market_order(ticker, quantity=qty)
            audit.log_order(
                cycle=self._cycle_num,
                symbol=sym,
                side="buy",
                shares=qty,
                price=price,
                reason=reason,
                success=True,
                equity=self._last_equity,
                free_cash=self._last_free_cash,
                dry_run=False,
            )
            return True
        except Exception as exc:
            log.error("  [%s] BUY order failed: %s", sym, exc)
            err_l = str(exc).lower()
            if "insufficient" in err_l or "free-for-stocks" in err_l:
                self._buy_fail_cycle[sym] = self._cycle_num
            audit.log_order(
                cycle=self._cycle_num,
                symbol=sym,
                side="buy",
                shares=shares,
                price=price,
                reason=reason,
                success=False,
                error=str(exc),
                equity=self._last_equity,
                free_cash=self._last_free_cash,
                dry_run=False,
            )
            return False

    def _sell(
        self,
        sym: str,
        shares: float,
        price: float,
        reason: str,
        pnl_eur: Optional[float] = None,
        broker_qty: Optional[float] = None,
    ) -> bool:
        if broker_qty is not None and broker_qty <= BROKER_QTY_EPS:
            log.warning("  [%s] SELL skipped – broker quantity is zero", sym)
            audit.log_order(
                cycle=self._cycle_num,
                symbol=sym,
                side="sell",
                shares=shares,
                price=price,
                reason=reason,
                success=False,
                error="broker_qty_zero",
                pnl_eur=pnl_eur,
                equity=self._last_equity,
                free_cash=self._last_free_cash,
                dry_run=self.dry_run,
            )
            return False
        if broker_qty is not None and shares > broker_qty + BROKER_QTY_EPS:
            log.warning(
                "  [%s] SELL capped %.4f → %.4f (broker holding)",
                sym, shares, broker_qty,
            )
            shares = broker_qty

        ticker = self.ticker_map.get(sym)
        if not ticker:
            log.warning("  [%s] no T212 ticker – cannot place sell order", sym)
            audit.log_order(
                cycle=self._cycle_num,
                symbol=sym,
                side="sell",
                shares=shares,
                price=price,
                reason=reason,
                success=False,
                error="no_t212_ticker",
                pnl_eur=pnl_eur,
                equity=self._last_equity,
                free_cash=self._last_free_cash,
                dry_run=self.dry_run,
            )
            return False
        if self.dry_run:
            log.info("  [DRY RUN] would SELL %s  %.4f shares @ ~%.4f  (%s)", sym, shares, price, reason)
            audit.log_order(
                cycle=self._cycle_num,
                symbol=sym,
                side="sell",
                shares=shares,
                price=price,
                reason=reason,
                success=True,
                pnl_eur=pnl_eur,
                equity=self._last_equity,
                free_cash=self._last_free_cash,
                dry_run=True,
            )
            return True
        try:
            qty = -abs(round(shares, 4))   # negative = sell
            self.client.place_market_order(ticker, quantity=qty)
            audit.log_order(
                cycle=self._cycle_num,
                symbol=sym,
                side="sell",
                shares=abs(qty),
                price=price,
                reason=reason,
                success=True,
                pnl_eur=pnl_eur,
                equity=self._last_equity,
                free_cash=self._last_free_cash,
                dry_run=False,
            )
            return True
        except Exception as exc:
            log.error("  [%s] SELL order failed: %s", sym, exc)
            audit.log_order(
                cycle=self._cycle_num,
                symbol=sym,
                side="sell",
                shares=shares,
                price=price,
                reason=reason,
                success=False,
                error=str(exc),
                pnl_eur=pnl_eur,
                equity=self._last_equity,
                free_cash=self._last_free_cash,
                dry_run=False,
            )
            return False


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="t212_miner_bot live trader")
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute signals but place NO orders")
    parser.add_argument("--once",    action="store_true",
                        help="Run one cycle immediately then exit")
    args = parser.parse_args()

    trader = LiveTrader(dry_run=args.dry_run)
    trader.run(run_once=args.once)


if __name__ == "__main__":
    main()
