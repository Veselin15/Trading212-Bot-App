"""
Trading 212 4-stock strategy comparison (5m + 15m logic).

This runner compares:
- BASELINE: current live-style management flow (+ optional costs and trade cap)
- ATR_DYNAMIC: ATR-based dynamic risk mode (+ optional costs and trade cap)

Both variants use the same core strategy structure as the Trading 212 bot:
EMA200 + DTosc regime/trigger on 5m and mapped 15m indicators,
pending stop entries, virtual Unit1 TP split, and Unit2 trailing stop.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import math
import sys
from dataclasses import dataclass, replace
from datetime import UTC, date as dt_date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from t212_miner_bot.backtests.t212_oos_regime_backtest import CFG, _compute_signal
from t212_miner_bot.config import SYMBOLS_MAP, StrategyParams
from t212_miner_bot.data_feed import _build_signal_snapshot
from t212_miner_bot.indicators import add_indicators


BREAK_EVEN_TRIGGER_PCT = 0.01
ZERO_PNL_TOLERANCE = 1e-8


@dataclass
class VariantMetrics:
    symbol: str
    variant: str
    total_return: float
    win_rate: float
    total_trades: int
    break_even_rate: float
    profit_factor: float


@dataclass
class SimConfig:
    fee_bps: float
    slippage_bps: float
    max_trades_per_day: int
    atr_stop_multiplier: float = 1.5
    atr_tp_r: float = 3.0
    atr_be_r: float = 1.0
    # BASE-mode runner trail (Unit2 after Unit1 TP): high_since_entry - atr_trail_mult * atr_15m
    atr_trail_mult: float = 2.5
    morning_protect_enabled: bool = False
    morning_real_profit_trigger_pct: float = 0.01
    morning_profit_capture_pct: float = 0.25
    morning_protect_window_minutes: int = 120
    morning_protect_symbol_enabled: dict[str, bool] | None = None


ENTRY_FILTER_ATR_MULT = 0.10
ENHANCED_ATR_PARAMS_BY_SYMBOL: dict[str, tuple[float, float, float]] = {
    # symbol: (stop_mult, tp_r, be_r)
    "ASML.AS": (2.8, 4.2, 2.2),
    "SAP.DE": (2.2, 4.0, 1.8),
    "SHELL.AS": (2.6, 3.6, 2.0),
    "UNA.AS": (2.3, 4.0, 1.8),
}

REGIME_ADAPTIVE_ATR_PROFILES: dict[str, tuple[float, float, float]] = {
    # regime: (stop_mult, tp_r, be_r)
    "TREND_STRONG": (2.8, 4.5, 2.2),
    "TREND_NORMAL": (2.5, 4.0, 2.0),
    "CHOP_WEAK": (2.0, 3.0, 1.2),
}


def _classify_regime_label(df: pd.DataFrame, i: int) -> str:
    if i < 3:
        return "TREND_NORMAL"
    row = df.iloc[i]
    prev = df.iloc[i - 1]
    prev2 = df.iloc[i - 2]

    close_i = float(row["close"])
    ema_15m = float(row["ema_15m"]) if pd.notna(row.get("ema_15m")) else float("nan")
    ema_15m_prev = float(prev["ema_15m"]) if pd.notna(prev.get("ema_15m")) else float("nan")
    ema_15m_prev2 = float(prev2["ema_15m"]) if pd.notna(prev2.get("ema_15m")) else float("nan")
    fast_15m = float(row["fast_15m"]) if pd.notna(row.get("fast_15m")) else float("nan")
    slow_15m = float(row["slow_15m"]) if pd.notna(row.get("slow_15m")) else float("nan")
    fast_5m = float(row["fast_5m"]) if pd.notna(row.get("fast_5m")) else float("nan")
    slow_5m = float(row["slow_5m"]) if pd.notna(row.get("slow_5m")) else float("nan")

    if not all(
        math.isfinite(v)
        for v in (ema_15m, ema_15m_prev, ema_15m_prev2, fast_15m, slow_15m, fast_5m, slow_5m)
    ):
        return "TREND_NORMAL"

    ema_up = ema_15m > ema_15m_prev > ema_15m_prev2
    trend_up = close_i > ema_15m and fast_15m > slow_15m and fast_5m > slow_5m

    if ema_up and trend_up:
        return "TREND_STRONG"
    if close_i < ema_15m or fast_15m <= slow_15m or fast_5m <= slow_5m:
        return "CHOP_WEAK"
    return "TREND_NORMAL"


def _entry_quality_pass(
    df: pd.DataFrame,
    i: int,
    mode: str,
    param: float,
) -> bool:
    mode_u = str(mode).strip().upper()
    if mode_u in {"", "NONE"}:
        return True

    if i < 2:
        return False
    row = df.iloc[i]
    prev = df.iloc[i - 1]
    close_i = float(row["close"])
    prev_high = float(prev["high"])
    atr_5m = float(row["atr_5m"]) if pd.notna(row["atr_5m"]) else 0.0
    if not math.isfinite(atr_5m) or atr_5m <= 0:
        return False

    if mode_u == "BREAKOUT_ATR":
        required_breakout = prev_high + (param * atr_5m)
        return close_i > required_breakout

    if mode_u == "PULLBACK_EMA":
        ema_15m = float(row["ema_15m"]) if pd.notna(row["ema_15m"]) else float("nan")
        if not math.isfinite(ema_15m):
            return False
        # Require trend alignment and a controlled pullback distance from EMA.
        return close_i > ema_15m and (close_i - ema_15m) <= (param * atr_5m)

    if mode_u == "COMPRESSION_BREAK":
        window = 6
        if i < window:
            return False
        recent_high = float(df["high"].iloc[i - window : i].max())
        recent_low = float(df["low"].iloc[i - window : i].min())
        compression_ratio = (recent_high - recent_low) / atr_5m
        return compression_ratio <= param and close_i > prev_high

    return True


def _parse_symbol_mode_map(raw: str) -> dict[str, str]:
    """
    Parse mapping like:
    "ASML.AS=BASE,SHELL.AS=BASE,SAP.DE=ATR,UNA.AS=ATR"
    """
    if not raw.strip():
        return {}
    out: dict[str, str] = {}
    for token in raw.split(","):
        part = token.strip()
        if not part or "=" not in part:
            continue
        symbol, mode = part.split("=", 1)
        symbol = symbol.strip()
        mode = mode.strip().upper()
        if symbol and mode in {"BASE", "ATR"}:
            out[symbol] = mode
    return out


def _parse_symbol_bool_map(raw: str) -> dict[str, bool]:
    """
    Parse mapping like:
    "ASML.AS=1,SAP.DE=true,SHELL.AS=0,UNA.AS=false"
    """
    if not raw.strip():
        return {}
    out: dict[str, bool] = {}
    truthy = {"1", "true", "yes", "on"}
    falsy = {"0", "false", "no", "off"}
    for token in raw.split(","):
        part = token.strip()
        if not part or "=" not in part:
            continue
        symbol, raw_flag = part.split("=", 1)
        symbol = symbol.strip()
        flag = raw_flag.strip().lower()
        if not symbol:
            continue
        if flag in truthy:
            out[symbol] = True
        elif flag in falsy:
            out[symbol] = False
    return out


def _profit_factor(trade_pnls: list[float]) -> float:
    gross_profit = sum(p for p in trade_pnls if p > 0)
    gross_loss = -sum(p for p in trade_pnls if p < 0)
    if gross_loss == 0:
        return math.inf if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def _cost_adjusted_return(raw_return: float, qty_fraction: float, fee_rate: float, slippage_rate: float) -> float:
    # Apply roundtrip costs on each executed leg in return-space.
    # qty_fraction is in [0,1] for split exits.
    return raw_return - (qty_fraction * 2.0 * (fee_rate + slippage_rate))


def _morning_protect_stop_candidate(
    *,
    symbol: str,
    ts: pd.Timestamp,
    session_open_ts: pd.Timestamp | None,
    entry_ts: pd.Timestamp | None,
    entry: float,
    stop: float,
    close_i: float,
    high_since_entry: float,
    config: SimConfig,
) -> float | None:
    if not config.morning_protect_enabled:
        return None
    symbol_flags = config.morning_protect_symbol_enabled or {}
    if symbol in symbol_flags and not bool(symbol_flags.get(symbol)):
        return None
    if entry_ts is None:
        return None
    if session_open_ts is None:
        return None
    if close_i <= 0:
        return None

    if ts.date() <= entry_ts.date():
        return None

    elapsed = ts - session_open_ts
    if elapsed < pd.Timedelta(0):
        return None
    if elapsed > pd.Timedelta(minutes=max(int(config.morning_protect_window_minutes), 1)):
        return None

    peak_profit_pct = (high_since_entry - entry) / entry if entry > 0 else 0.0
    if peak_profit_pct >= config.morning_real_profit_trigger_pct:
        return None

    current_profit = max(close_i - entry, 0.0)
    candidate = max(entry, entry + (config.morning_profit_capture_pct * current_profit))
    max_valid_stop = close_i * 0.9995
    if candidate >= max_valid_stop:
        return None
    if candidate <= stop:
        return None
    return candidate


def _simulate_symbol_variant(
    df_raw: pd.DataFrame,
    symbol: str,
    enable_break_even_1pct: bool,
    config: SimConfig,
    entry_filter_atr_mult: float = 0.0,
    entry_filter_mode: str = "NONE",
    entry_filter_param: float = 0.0,
    profit_lock_trigger_pct: float = 0.0,
    profit_lock_stop_pct: float = 0.0,
) -> VariantMetrics:
    df = add_indicators(df_raw, ema_period=CFG.ema_period).dropna().copy()
    if df.empty or len(df) < 100:
        return VariantMetrics(
            symbol=symbol,
            variant="BE_1PCT" if enable_break_even_1pct else "BASELINE",
            total_return=0.0,
            win_rate=0.0,
            total_trades=0,
            break_even_rate=0.0,
            profit_factor=0.0,
        )

    pending: dict[str, Any] | None = None
    position: dict[str, Any] | None = None
    equity = 1.0
    trade_pnls: list[float] = []
    break_even_saved = 0
    fee_rate = config.fee_bps / 10_000.0
    slippage_rate = config.slippage_bps / 10_000.0
    trades_by_day: dict[str, int] = {}
    first_bar_by_day: dict[dt_date, pd.Timestamp] = {}

    for i in range(2, len(df)):
        row = df.iloc[i]
        ts = df.index[i]
        day_key = str(ts.date())
        if ts.date() not in first_bar_by_day:
            first_bar_by_day[ts.date()] = ts
        session_open_ts = first_bar_by_day.get(ts.date())
        high_i = float(row["high"])
        low_i = float(row["low"])
        close_i = float(row["close"])
        atr_15m = float(row["atr_15m"]) if pd.notna(row["atr_15m"]) else 0.0

        # Manage open position first.
        if position is not None:
            entry = float(position["entry"])
            stop = float(position["stop"])
            qty_open = float(position["qty_open"])
            unit1_tp = float(position["unit1_tp"])
            unit1_done = bool(position["unit1_done"])
            high_since_entry = float(position["high_since_entry"])
            realized_pnl = float(position["realized_pnl"])
            break_even_moved = bool(position.get("break_even_moved", False))
            entry_time = position.get("entry_time")
            entry_time_ts = entry_time if isinstance(entry_time, pd.Timestamp) else None

            # New feature under test: once +1% is reached, move stop to entry.
            if enable_break_even_1pct and (not break_even_moved) and high_i >= entry * (1.0 + BREAK_EVEN_TRIGGER_PCT):
                stop = max(stop, entry)
                break_even_moved = True

            # Upgrade under test: when profit reaches higher tier, lock part of gains.
            if (
                profit_lock_trigger_pct > 0
                and profit_lock_stop_pct > 0
                and high_i >= entry * (1.0 + profit_lock_trigger_pct)
            ):
                lock_stop = entry * (1.0 + profit_lock_stop_pct)
                stop = max(stop, lock_stop)

            morning_candidate = _morning_protect_stop_candidate(
                symbol=symbol,
                ts=ts,
                session_open_ts=session_open_ts,
                entry_ts=entry_time_ts,
                entry=entry,
                stop=stop,
                close_i=close_i,
                high_since_entry=high_since_entry,
                config=config,
            )
            if morning_candidate is not None:
                stop = max(stop, float(morning_candidate))

            # Conservative intrabar order: stop before any profit-taking checks.
            if low_i <= stop:
                leg_raw = qty_open * ((stop - entry) / entry)
                leg_net = _cost_adjusted_return(leg_raw, qty_open, fee_rate, slippage_rate)
                pnl_total = realized_pnl + leg_net
                equity *= 1.0 + pnl_total
                trade_pnls.append(pnl_total)
                if break_even_moved and abs(pnl_total) <= ZERO_PNL_TOLERANCE:
                    break_even_saved += 1
                position = None
                continue

            # Unit1 virtual TP at close.
            if (not unit1_done) and close_i >= unit1_tp:
                closed_qty = 0.5
                leg_raw = closed_qty * ((close_i - entry) / entry)
                realized_pnl += _cost_adjusted_return(leg_raw, closed_qty, fee_rate, slippage_rate)
                qty_open -= closed_qty
                unit1_done = True
                # Keep baseline behavior.
                stop = max(stop, entry * (1.0 + CFG.breakeven_offset_pct))

            # Unit2 trailing after Unit1 completion.
            if unit1_done and qty_open > 0:
                high_since_entry = max(high_since_entry, high_i)
                if atr_15m > 0:
                    trail_mult = max(float(getattr(config, "atr_trail_mult", CFG.atr_trail_mult)), 0.1)
                    trail_stop = high_since_entry - (trail_mult * atr_15m)
                    stop = max(stop, trail_stop)
                if low_i <= stop:
                    leg_raw = qty_open * ((stop - entry) / entry)
                    leg_net = _cost_adjusted_return(leg_raw, qty_open, fee_rate, slippage_rate)
                    pnl_total = realized_pnl + leg_net
                    equity *= 1.0 + pnl_total
                    trade_pnls.append(pnl_total)
                    if break_even_moved and abs(pnl_total) <= ZERO_PNL_TOLERANCE:
                        break_even_saved += 1
                    position = None
                    continue

            position["stop"] = stop
            position["qty_open"] = qty_open
            position["unit1_done"] = unit1_done
            position["high_since_entry"] = high_since_entry
            position["realized_pnl"] = realized_pnl
            position["break_even_moved"] = break_even_moved
            continue

        # Pending stop-entry management.
        if pending is not None:
            signal_snapshot = _compute_signal(df, i)
            if high_i >= float(pending["entry_stop"]):
                entry = float(pending["entry_stop"])
                risk = float(pending["risk_distance"])
                if risk > 0:
                    position = {
                        "entry_time": ts,
                        "entry": entry,
                        "stop": entry - risk,
                        "unit1_tp": entry + (CFG.unit1_tp_rr * risk),
                        "qty_open": 1.0,
                        "unit1_done": False,
                        "high_since_entry": high_i,
                        "realized_pnl": 0.0,
                        "break_even_moved": False,
                    }
                pending = None
            else:
                if signal_snapshot["momentum_ok"]:
                    pending["entry_stop"] = min(float(pending["entry_stop"]), high_i)
                else:
                    pending = None
            continue

        # New long signal.
        snapshot = _compute_signal(df, i)
        if not snapshot["long_signal"]:
            continue
        eff_mode = entry_filter_mode
        eff_param = entry_filter_param
        if entry_filter_atr_mult > 0 and str(entry_filter_mode).strip().upper() in {"", "NONE"}:
            eff_mode = "BREAKOUT_ATR"
            eff_param = entry_filter_atr_mult
        if not _entry_quality_pass(df=df, i=i, mode=eff_mode, param=eff_param):
            continue
        if trades_by_day.get(day_key, 0) >= config.max_trades_per_day:
            continue

        risk_distance = CFG.atr_multiplier * snapshot["atr_5m"]
        if risk_distance <= 0:
            continue

        pending = {"entry_stop": snapshot["signal_high"], "risk_distance": risk_distance}
        trades_by_day[day_key] = trades_by_day.get(day_key, 0) + 1

    # End-of-data close.
    if position is not None:
        entry = float(position["entry"])
        qty_open = float(position["qty_open"])
        realized_pnl = float(position["realized_pnl"])
        last_close = float(df["close"].iloc[-1])
        leg_raw = qty_open * ((last_close - entry) / entry)
        leg_net = _cost_adjusted_return(leg_raw, qty_open, fee_rate, slippage_rate)
        pnl_total = realized_pnl + leg_net
        equity *= 1.0 + pnl_total
        trade_pnls.append(pnl_total)
        if bool(position.get("break_even_moved", False)) and abs(pnl_total) <= ZERO_PNL_TOLERANCE:
            break_even_saved += 1

    total_trades = len(trade_pnls)
    win_rate = (sum(1 for p in trade_pnls if p > 0) / total_trades * 100.0) if total_trades else 0.0
    break_even_rate = (break_even_saved / total_trades * 100.0) if total_trades else 0.0
    total_return = (equity - 1.0) * 100.0
    pf = _profit_factor(trade_pnls)

    return VariantMetrics(
        symbol=symbol,
        variant="BE_1PCT" if enable_break_even_1pct else "BASELINE",
        total_return=total_return,
        win_rate=win_rate,
        total_trades=total_trades,
        break_even_rate=break_even_rate,
        profit_factor=pf,
    )


def _simulate_atr_dynamic_variant(
    df_raw: pd.DataFrame,
    symbol: str,
    config: SimConfig,
    *,
    stop_mult: float | None = None,
    tp_r: float | None = None,
    be_r: float | None = None,
    entry_filter_atr_mult: float = 0.0,
    entry_filter_mode: str = "NONE",
    entry_filter_param: float = 0.0,
    regime_adaptive: bool = False,
    regime_profiles: dict[str, tuple[float, float, float]] | None = None,
    profit_lock_trigger_pct: float = 0.0,
    profit_lock_stop_pct: float = 0.0,
) -> VariantMetrics:
    df = add_indicators(df_raw, ema_period=CFG.ema_period).dropna().copy()
    if df.empty or len(df) < 100:
        return VariantMetrics(
            symbol=symbol,
            variant="ATR_DYNAMIC",
            total_return=0.0,
            win_rate=0.0,
            total_trades=0,
            break_even_rate=0.0,
            profit_factor=0.0,
        )

    capital = 10_000.0
    risk_pct = 0.02
    position: dict[str, float | bool] | None = None
    trade_pnls: list[float] = []
    break_even_saved = 0
    fee_rate = config.fee_bps / 10_000.0
    slippage_rate = config.slippage_bps / 10_000.0
    trades_by_day: dict[str, int] = {}
    first_bar_by_day: dict[dt_date, pd.Timestamp] = {}
    stop_mult_eff = float(stop_mult if stop_mult is not None else config.atr_stop_multiplier)
    tp_r_eff = float(tp_r if tp_r is not None else config.atr_tp_r)
    be_r_eff = float(be_r if be_r is not None else config.atr_be_r)
    profiles = regime_profiles or REGIME_ADAPTIVE_ATR_PROFILES

    for i in range(2, len(df)):
        current_slice = df.iloc[: i + 1]
        row = current_slice.iloc[-1]
        ts = current_slice.index[-1]
        day_key = str(ts.date())
        if ts.date() not in first_bar_by_day:
            first_bar_by_day[ts.date()] = ts
        session_open_ts = first_bar_by_day.get(ts.date())
        high_i = float(row["high"])
        low_i = float(row["low"])
        close_i = float(row["close"])

        if position is not None:
            entry = float(position["entry"])
            stop = float(position["stop"])
            target = float(position["target"])
            qty = float(position["qty"])
            risk_distance = float(position["risk_distance"])
            be_activated = bool(position["be_activated"])
            high_since_entry = float(position.get("high_since_entry", entry))
            high_since_entry = max(high_since_entry, high_i)
            entry_time = position.get("entry_time")
            entry_time_ts = entry_time if isinstance(entry_time, pd.Timestamp) else None

            be_r_active = float(position.get("be_r_active", be_r_eff))
            if (not be_activated) and high_i >= entry + (be_r_active * risk_distance):
                stop = max(stop, entry)
                be_activated = True

            if (
                profit_lock_trigger_pct > 0
                and profit_lock_stop_pct > 0
                and high_i >= entry * (1.0 + profit_lock_trigger_pct)
            ):
                lock_stop = entry * (1.0 + profit_lock_stop_pct)
                stop = max(stop, lock_stop)

            morning_candidate = _morning_protect_stop_candidate(
                symbol=symbol,
                ts=ts,
                session_open_ts=session_open_ts,
                entry_ts=entry_time_ts,
                entry=entry,
                stop=stop,
                close_i=close_i,
                high_since_entry=high_since_entry,
                config=config,
            )
            if morning_candidate is not None:
                stop = max(stop, float(morning_candidate))

            # Conservative intrabar sequence: stop first.
            exit_price: float | None = None
            if low_i <= stop:
                exit_price = stop
            elif high_i >= target:
                exit_price = target

            if exit_price is not None:
                # Apply slippage+fees on both sides in price space.
                entry_exec = entry * (1.0 + slippage_rate)
                exit_exec = exit_price * (1.0 - slippage_rate)
                gross = (exit_exec - entry_exec) * qty
                fees = fee_rate * ((entry_exec * qty) + (exit_exec * qty))
                pnl = gross - fees
                capital += pnl
                trade_pnls.append(pnl)
                if be_activated and abs(pnl) <= ZERO_PNL_TOLERANCE:
                    break_even_saved += 1
                position = None
            else:
                position["stop"] = stop
                position["be_activated"] = be_activated
                position["high_since_entry"] = high_since_entry
            continue

        snapshot = _build_signal_snapshot(current_slice)
        if not snapshot.get("ready"):
            continue
        if str(snapshot.get("signal_side", "none")) != "long":
            continue
        if trades_by_day.get(day_key, 0) >= config.max_trades_per_day:
            continue

        atr_5m = float(snapshot.get("atr_5m", 0.0))
        if not math.isfinite(atr_5m) or atr_5m <= 0:
            continue
        eff_mode = entry_filter_mode
        eff_param = entry_filter_param
        if entry_filter_atr_mult > 0 and str(entry_filter_mode).strip().upper() in {"", "NONE"}:
            eff_mode = "BREAKOUT_ATR"
            eff_param = entry_filter_atr_mult
        if not _entry_quality_pass(df=df, i=i, mode=eff_mode, param=eff_param):
            continue
        stop_mult_active = stop_mult_eff
        tp_r_active = tp_r_eff
        be_r_active = be_r_eff
        if regime_adaptive:
            regime_label = _classify_regime_label(df=df, i=i)
            stop_mult_active, tp_r_active, be_r_active = profiles.get(
                regime_label,
                (stop_mult_eff, tp_r_eff, be_r_eff),
            )

        risk_distance = stop_mult_active * atr_5m
        if risk_distance <= 0:
            continue

        entry = float(snapshot["close"])
        risk_amount = capital * risk_pct
        qty = risk_amount / risk_distance
        if qty <= 0:
            continue

        position = {
            "entry_time": ts,
            "entry": entry,
            "stop": entry - risk_distance,
            "target": entry + (tp_r_active * risk_distance),
            "qty": qty,
            "risk_distance": risk_distance,
            "be_activated": False,
            "be_r_active": be_r_active,
            "high_since_entry": high_i,
        }
        trades_by_day[day_key] = trades_by_day.get(day_key, 0) + 1

    if position is not None:
        entry = float(position["entry"])
        qty = float(position["qty"])
        be_activated = bool(position["be_activated"])
        last_close = float(df["close"].iloc[-1])
        entry_exec = entry * (1.0 + slippage_rate)
        exit_exec = last_close * (1.0 - slippage_rate)
        gross = (exit_exec - entry_exec) * qty
        fees = fee_rate * ((entry_exec * qty) + (exit_exec * qty))
        pnl = gross - fees
        capital += pnl
        trade_pnls.append(pnl)
        if be_activated and abs(pnl) <= ZERO_PNL_TOLERANCE:
            break_even_saved += 1

    total_trades = len(trade_pnls)
    win_rate = (sum(1 for p in trade_pnls if p > 0) / total_trades * 100.0) if total_trades else 0.0
    break_even_rate = (break_even_saved / total_trades * 100.0) if total_trades else 0.0
    total_return = (capital / 10_000.0 - 1.0) * 100.0
    pf = _profit_factor(trade_pnls)
    return VariantMetrics(
        symbol=symbol,
        variant="ATR_DYNAMIC",
        total_return=total_return,
        win_rate=win_rate,
        total_trades=total_trades,
        break_even_rate=break_even_rate,
        profit_factor=pf,
    )


def _load_local_5m_csv(symbol: str, days: int) -> pd.DataFrame:
    # Prefer local historical data for multi-month/multi-year intraday backtests.
    data_dir = REPO_ROOT / "data"
    candidates = [f"{symbol}_5m.csv"]
    # Historical file naming compatibility for Shell in this repository.
    if symbol == "SHELL.AS":
        candidates.append("SHEL.AS_5m.csv")

    source_path: Path | None = None
    for name in candidates:
        candidate = data_dir / name
        if candidate.exists():
            source_path = candidate
            break
    if source_path is None:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    try:
        df = pd.read_csv(source_path)
    except Exception:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    required = {"timestamp", "open", "high", "low", "close", "volume"}
    if not required.issubset(set(df.columns)):
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    out = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out = out.dropna(subset=["timestamp", "open", "high", "low", "close"]).sort_values("timestamp")
    out = out.set_index("timestamp")

    end = pd.Timestamp.now(tz="UTC")
    start = end - pd.Timedelta(days=days)
    out = out[(out.index >= start) & (out.index <= end)].copy()
    return out if not out.empty else df[["open", "high", "low", "close", "volume"]].copy()


def _download_5m_recent(symbol: str, days: int) -> pd.DataFrame:
    # Yahoo 5m endpoint is limited, keep this only as a short-window fallback.
    effective_days = max(1, min(days, 59))
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        raw = yf.Ticker(symbol).history(period=f"{effective_days}d", interval="5m", auto_adjust=False)
    if raw.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [col[0] if isinstance(col, tuple) else col for col in raw.columns]
    bars = raw.rename(
        columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}
    )
    required = ["open", "high", "low", "close", "volume"]
    if any(col not in bars.columns for col in required):
        return pd.DataFrame(columns=required)
    out = bars[required].dropna(subset=["open", "high", "low", "close"]).copy()
    if out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    return out


def run_comparison(
    days: int,
    config: SimConfig,
    symbol_mode_map: dict[str, str],
    *,
    enhanced_entry_filter_mode: str = "NONE",
    enhanced_entry_filter_param: float = 0.0,
    enhanced_atr_params_by_symbol: dict[str, tuple[float, float, float]] | None = None,
    enhanced_regime_adaptive: bool = False,
    enhanced_regime_profiles: dict[str, tuple[float, float, float]] | None = None,
    profit_lock_trigger_pct: float = 0.0,
    profit_lock_stop_pct: float = 0.0,
) -> None:
    symbols = list(SYMBOLS_MAP.keys())
    live_config = replace(config, morning_protect_enabled=False)
    enhanced_config = config

    live_hybrid: dict[str, VariantMetrics] = {}
    enhanced_hybrid: dict[str, VariantMetrics] = {}
    params = StrategyParams()
    effective_mode_map = symbol_mode_map if symbol_mode_map else params.symbol_strategy_mode
    enhanced_atr_map = enhanced_atr_params_by_symbol or {}
    regime_profiles = enhanced_regime_profiles or REGIME_ADAPTIVE_ATR_PROFILES

    print(
        f"[INFO] Running CURRENT vs ENHANCED comparison | Days={days} | "
        f"Universe={', '.join(symbols)} | "
        f"fee_bps={config.fee_bps:.2f} slippage_bps={config.slippage_bps:.2f} "
        f"max_trades_per_day={config.max_trades_per_day}"
    )

    for symbol in symbols:
        bars = _load_local_5m_csv(symbol=symbol, days=days)
        data_source = "local_csv"
        if bars.empty:
            bars = _download_5m_recent(symbol=symbol, days=days)
            data_source = "yahoo_recent"

        if bars.empty:
            print(f"[WARN] {symbol}: no bars available, skipping.")
            continue
        print(f"[INFO] {symbol}: using {len(bars)} bars from {data_source}.")

        base_std = _simulate_symbol_variant(
            bars,
            symbol,
            enable_break_even_1pct=False,
            config=live_config,
            entry_filter_atr_mult=0.0,
            profit_lock_trigger_pct=profit_lock_trigger_pct,
            profit_lock_stop_pct=profit_lock_stop_pct,
        )
        atr_std = _simulate_atr_dynamic_variant(
            bars,
            symbol,
            config=live_config,
            entry_filter_atr_mult=0.0,
            profit_lock_trigger_pct=profit_lock_trigger_pct,
            profit_lock_stop_pct=profit_lock_stop_pct,
        )
        mode = str(effective_mode_map.get(symbol, "BASE")).strip().upper()
        live_hybrid[symbol] = base_std if mode == "BASE" else atr_std

        base_enh = _simulate_symbol_variant(
            bars,
            symbol,
            enable_break_even_1pct=False,
            config=enhanced_config,
            entry_filter_mode=enhanced_entry_filter_mode,
            entry_filter_param=enhanced_entry_filter_param,
            profit_lock_trigger_pct=profit_lock_trigger_pct,
            profit_lock_stop_pct=profit_lock_stop_pct,
        )
        stop_mult, tp_r, be_r = enhanced_atr_map.get(
            symbol,
            (enhanced_config.atr_stop_multiplier, enhanced_config.atr_tp_r, enhanced_config.atr_be_r),
        )
        atr_enh = _simulate_atr_dynamic_variant(
            bars,
            symbol,
            config=enhanced_config,
            stop_mult=stop_mult,
            tp_r=tp_r,
            be_r=be_r,
            entry_filter_mode=enhanced_entry_filter_mode,
            entry_filter_param=enhanced_entry_filter_param,
            regime_adaptive=enhanced_regime_adaptive,
            regime_profiles=regime_profiles,
            profit_lock_trigger_pct=profit_lock_trigger_pct,
            profit_lock_stop_pct=profit_lock_stop_pct,
        )
        enhanced_hybrid[symbol] = base_enh if mode == "BASE" else atr_enh

    print("\n" + "=" * 142)
    print("T212 CURRENT LIVE HYBRID VS ENHANCED HYBRID (ALL 4 STOCKS)")
    print("=" * 142)
    print(
        f"{'Symbol':<10} {'Live Ret%':>11} {'Enh Ret%':>10} {'Delta%':>10} "
        f"{'Live Trades':>12} {'Enh Trades':>10} {'Live Win%':>10} {'Enh Win%':>10} {'Enh BE%':>10} {'Enh PF':>10}"
    )
    print("-" * 142)

    live_returns: list[float] = []
    enh_returns: list[float] = []
    live_trade_total = 0
    enh_trade_total = 0
    live_wins_weighted = 0.0
    enh_wins_weighted = 0.0
    enh_saves_weighted = 0.0

    for symbol in symbols:
        l = live_hybrid.get(symbol)
        e = enhanced_hybrid.get(symbol)
        if l is None or e is None:
            print(
                f"{symbol:<10} {'N/A':>11} {'N/A':>10} {'N/A':>10} {'N/A':>12} "
                f"{'N/A':>10} {'N/A':>10} {'N/A':>10} {'N/A':>10} {'N/A':>10}"
            )
            continue

        delta = e.total_return - l.total_return
        pf_text = f"{e.profit_factor:.2f}" if math.isfinite(e.profit_factor) else "inf"
        hybrid_mode = str(effective_mode_map.get(symbol, "BASE")).strip().upper()
        print(
            f"{symbol:<10} {l.total_return:>11.2f} {e.total_return:>10.2f} {delta:>10.2f} "
            f"{l.total_trades:>12d} {e.total_trades:>10d} {l.win_rate:>10.2f} {e.win_rate:>10.2f} {e.break_even_rate:>10.2f} {pf_text:>10} "
            f"| MODE={hybrid_mode}"
        )

        live_returns.append(l.total_return)
        enh_returns.append(e.total_return)
        live_trade_total += l.total_trades
        enh_trade_total += e.total_trades
        live_wins_weighted += (l.win_rate / 100.0) * l.total_trades
        enh_wins_weighted += (e.win_rate / 100.0) * e.total_trades
        enh_saves_weighted += (e.break_even_rate / 100.0) * e.total_trades

    portfolio_live_return = float(np.mean(live_returns)) if live_returns else 0.0
    portfolio_enh_return = float(np.mean(enh_returns)) if enh_returns else 0.0
    portfolio_delta = portfolio_enh_return - portfolio_live_return
    portfolio_live_win = (live_wins_weighted / live_trade_total * 100.0) if live_trade_total else 0.0
    portfolio_enh_win = (enh_wins_weighted / enh_trade_total * 100.0) if enh_trade_total else 0.0
    portfolio_enh_rate = (enh_saves_weighted / enh_trade_total * 100.0) if enh_trade_total else 0.0

    print("-" * 142)
    print(
        f"{'PORTFOLIO':<10} {portfolio_live_return:>11.2f} {portfolio_enh_return:>10.2f} {portfolio_delta:>10.2f} "
        f"{live_trade_total:>12d} {enh_trade_total:>10d} {portfolio_live_win:>10.2f} {portfolio_enh_win:>10.2f} {portfolio_enh_rate:>10.2f} {'-':>10}"
    )
    print(f"[INFO] Current hybrid symbol modes: {effective_mode_map}")
    print(f"[INFO] Enhanced entry filter mode: {enhanced_entry_filter_mode}")
    print(f"[INFO] Enhanced entry filter param: {enhanced_entry_filter_param:.4f}")
    print(f"[INFO] Enhanced ATR params by symbol: {enhanced_atr_map}")
    print(f"[INFO] Enhanced regime-adaptive ATR: {enhanced_regime_adaptive}")
    print(
        "[INFO] Enhanced morning-protect: "
        f"enabled={enhanced_config.morning_protect_enabled} "
        f"real_profit_trigger={enhanced_config.morning_real_profit_trigger_pct:.4f} "
        f"profit_capture={enhanced_config.morning_profit_capture_pct:.4f} "
        f"window_min={enhanced_config.morning_protect_window_minutes}"
    )
    print(f"[INFO] Enhanced morning-protect symbol map: {enhanced_config.morning_protect_symbol_enabled}")
    if enhanced_regime_adaptive:
        print(f"[INFO] Enhanced regime profiles: {regime_profiles}")
    print(
        f"[INFO] Profit lock (both legs): trigger={profit_lock_trigger_pct:.4f} "
        f"stop={profit_lock_stop_pct:.4f}"
    )
    print("=" * 142)


def main() -> None:
    params = StrategyParams()
    parser = argparse.ArgumentParser(description="Compare baseline vs ATR dynamic on all 4 T212 stocks.")
    parser.add_argument("--days", type=int, default=730, help="Backtest lookback days (default: 730)")
    parser.add_argument("--fee-bps", type=float, default=0.0, help="Per-side fee in bps (default: 0.0).")
    parser.add_argument("--slippage-bps", type=float, default=5.0, help="Per-side slippage in bps (default: 5.0).")
    parser.add_argument(
        "--max-trades-per-day",
        type=int,
        default=9999,
        help="Max new entries per symbol per day (default: 9999).",
    )
    parser.add_argument(
        "--atr-stop-mult",
        type=float,
        default=float(params.atr_dynamic_stop_mult),
        help="ATR stop multiplier (default: from StrategyParams).",
    )
    parser.add_argument(
        "--atr-tp-r",
        type=float,
        default=float(params.atr_dynamic_tp_r),
        help="ATR take-profit in R (default: from StrategyParams).",
    )
    parser.add_argument(
        "--atr-be-r",
        type=float,
        default=float(params.atr_dynamic_be_r),
        help="ATR break-even trigger in R (default: from StrategyParams).",
    )
    parser.add_argument(
        "--symbol-modes",
        type=str,
        default="",
        help="Optional per-symbol mode map, e.g. ASML.AS=BASE,SHELL.AS=BASE,SAP.DE=ATR,UNA.AS=ATR",
    )
    parser.add_argument(
        "--morning-protect-enabled",
        type=int,
        default=1,
        help="Enable morning overnight-protection in ENHANCED leg (1=yes, 0=no). Default: 1.",
    )
    parser.add_argument(
        "--morning-real-profit-trigger-pct",
        type=float,
        default=float(params.morning_real_profit_trigger_pct),
        help="If peak unrealized profit before morning is below this, apply morning protect. Default: StrategyParams value.",
    )
    parser.add_argument(
        "--morning-profit-capture-pct",
        type=float,
        default=float(params.morning_profit_capture_pct),
        help="Fraction of current unrealized gain locked in morning protect stop. Default: StrategyParams value.",
    )
    parser.add_argument(
        "--morning-protect-window-minutes",
        type=int,
        default=int(params.morning_protect_window_minutes),
        help="Session-open window (minutes) where morning protect can apply. Default: StrategyParams value.",
    )
    parser.add_argument(
        "--morning-symbol-map",
        type=str,
        default="",
        help="Optional per-symbol morning protect map, e.g. ASML.AS=1,SAP.DE=1,SHELL.AS=0,UNA.AS=0",
    )
    args = parser.parse_args()
    parsed_morning_map = _parse_symbol_bool_map(args.morning_symbol_map)
    effective_morning_map = (
        parsed_morning_map if parsed_morning_map else dict(params.morning_protect_symbol_enabled)
    )
    config = SimConfig(
        fee_bps=max(args.fee_bps, 0.0),
        slippage_bps=max(args.slippage_bps, 0.0),
        max_trades_per_day=max(args.max_trades_per_day, 1),
        atr_stop_multiplier=max(args.atr_stop_mult, 0.1),
        atr_tp_r=max(args.atr_tp_r, 0.1),
        atr_be_r=max(args.atr_be_r, 0.1),
        morning_protect_enabled=bool(int(args.morning_protect_enabled)),
        morning_real_profit_trigger_pct=max(args.morning_real_profit_trigger_pct, 0.0),
        morning_profit_capture_pct=max(args.morning_profit_capture_pct, 0.0),
        morning_protect_window_minutes=max(int(args.morning_protect_window_minutes), 1),
        morning_protect_symbol_enabled=effective_morning_map,
    )
    run_comparison(
        days=args.days,
        config=config,
        symbol_mode_map=_parse_symbol_mode_map(args.symbol_modes),
        profit_lock_trigger_pct=float(params.profit_lock_trigger_pct),
        profit_lock_stop_pct=float(params.profit_lock_stop_pct),
    )


if __name__ == "__main__":
    main()
