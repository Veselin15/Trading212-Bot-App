"""
Compare BASE-mode trailing behavior:

Variant A (current live logic):
  - BASE: break-even + profit-lock in UNIT1_ACTIVE
  - BASE: trailing starts only after Virtual TP (UNIT2_ACTIVE)

Variant B (new experiment):
  - BASE: start ATR trailing already in UNIT1_ACTIVE *after* BE or profit-lock is active
    (prevents large givebacks during big runs before Virtual TP triggers)

We keep ATR-mode behavior unchanged (SAP.DE).

Notes on history length:
  The EU 5m datasets in this repo start around 2024-01-02, so "3 years" is
  not available at 5m granularity for these symbols. This script uses the
  maximum available history, and prints the actual date range used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from t212_miner_bot.backtests.t212_bulgaria_fee_tax_portfolio_test import (
    _discover_symbol_files,
    _fee_bps_per_side_for_symbol,
)
from t212_miner_bot.config import StrategyParams
from t212_miner_bot.indicators import add_indicators


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"

SYMBOLS = ["ASML.AS", "SAP.DE", "UNA.AS", "AMD"]
SYMBOL_MODE_MAP = {"ASML.AS": "BASE", "SAP.DE": "ATR", "UNA.AS": "BASE", "AMD": "BASE"}

EMA_PERIOD = 200
MAX_TRADES_PER_DAY = 2
SLIPPAGE_BPS = 10.0


@dataclass(frozen=True)
class Candidate:
    label: str
    atr_stop: float
    tp_rr: float
    be_r: float
    be_pct: float
    trail_mult: float
    lock_trigger: float
    lock_stop: float
    trail_in_unit1: bool


@dataclass
class SymArrays:
    n: int
    close: np.ndarray
    high: np.ndarray
    low: np.ndarray
    atr5: np.ndarray
    atr15: np.ndarray
    ema15: np.ndarray
    fast5: np.ndarray
    slow5: np.ndarray
    fast15: np.ndarray
    slow15: np.ndarray
    long_sig: np.ndarray
    blocked: np.ndarray
    day_idx: np.ndarray


def _precompute(df: pd.DataFrame) -> SymArrays:
    n = len(df)
    close = df["close"].to_numpy(float)
    high = df["high"].to_numpy(float)
    low = df["low"].to_numpy(float)
    atr5 = df["atr_5m"].to_numpy(float)
    atr15 = df["atr_15m"].to_numpy(float)
    ema15 = df["ema_15m"].to_numpy(float)
    fast5 = df["fast_5m"].to_numpy(float)
    slow5 = df["slow_5m"].to_numpy(float)
    fast15 = df["fast_15m"].to_numpy(float)
    slow15 = df["slow_15m"].to_numpy(float)

    long_sig = np.zeros(n, dtype=bool)
    for i in range(2, n):
        if not (math.isfinite(ema15[i]) and math.isfinite(fast15[i]) and math.isfinite(fast5[i])):
            continue
        regime_long = (close[i] > ema15[i]) and (fast15[i] > slow15[i]) and (fast15[i] < 75.0)
        trigger = (fast5[i - 1] <= slow5[i - 1]) and (fast5[i] > slow5[i]) and (fast5[i] < 75.0)
        long_sig[i] = regime_long and trigger

    blocked = np.zeros(n, dtype=bool)
    for i, ts in enumerate(df.index):
        # lunch block and EU open buffer (UTC-based approximation consistent with repo)
        if (ts.hour == 11 and ts.minute >= 55) or (ts.hour == 12 and ts.minute <= 35):
            blocked[i] = True
        if (ts.hour == 7 and ts.minute >= 55) or (ts.hour == 8 and ts.minute <= 15):
            blocked[i] = True

    dates = np.array([ts.date() for ts in df.index])
    _, day_idx = np.unique(dates, return_inverse=True)

    return SymArrays(
        n=n,
        close=close,
        high=high,
        low=low,
        atr5=atr5,
        atr15=atr15,
        ema15=ema15,
        fast5=fast5,
        slow5=slow5,
        fast15=fast15,
        slow15=slow15,
        long_sig=long_sig,
        blocked=blocked,
        day_idx=day_idx,
    )


def _sim_base(arr: SymArrays, cand: Candidate, fee_r: float, slip_r: float) -> float:
    """
    BASE mode: pending stop-entry at signal high; unit1 virtual TP; unit2 trailing.
    Experiment: optional trailing during UNIT1_ACTIVE after BE/profit-lock is active.
    Returns total return %.
    """
    n = arr.n
    equity = 1.0
    day_trade_cnt: dict[int, int] = {}

    in_pos = False
    pending = False
    pend_stop = 0.0
    pend_risk = 0.0

    entry_p = 0.0
    stop_p = 0.0
    unit1_tp = 0.0
    qty_open = 0.0
    unit1_done = False
    high_pk = 0.0
    realized = 0.0
    be_moved = False
    pl_moved = False

    def cost_adj(ret_frac: float, qty_frac: float) -> float:
        # Conservative: fees as fraction + slippage both sides.
        return ret_frac * (1.0 - fee_r) - slip_r * 2.0 * qty_frac

    for i in range(2, n):
        hi = arr.high[i]
        lo = arr.low[i]
        cl = arr.close[i]
        a15 = arr.atr15[i]
        day = int(arr.day_idx[i])

        if in_pos:
            high_pk = max(high_pk, hi)

            # Break-even (BASE uses % trigger)
            if not be_moved and hi >= entry_p * (1.0 + cand.be_pct):
                stop_p = max(stop_p, entry_p)
                be_moved = True

            # Profit lock
            if cand.lock_trigger > 0 and hi >= entry_p * (1.0 + cand.lock_trigger):
                lock_stop = entry_p * (1.0 + cand.lock_stop)
                if lock_stop > stop_p:
                    stop_p = lock_stop
                    pl_moved = True

            # Experimental: start trailing already in UNIT1_ACTIVE, but only once risk is reduced
            # (after BE or profit-lock) to avoid tightening too early.
            if (cand.trail_in_unit1 and (be_moved or pl_moved) and (not unit1_done)
                    and math.isfinite(a15) and a15 > 0):
                trail = high_pk - cand.trail_mult * a15
                if trail > stop_p:
                    stop_p = trail

            # Stop hit
            if lo <= stop_p:
                leg = qty_open * ((stop_p - entry_p) / entry_p)
                pnl = realized + cost_adj(leg, qty_open)
                equity *= 1.0 + pnl
                in_pos = False
                continue

            # Unit1 TP
            if not unit1_done and cl >= unit1_tp:
                half = 0.5
                raw = half * ((cl - entry_p) / entry_p)
                realized += cost_adj(raw, half)
                qty_open -= half
                unit1_done = True
                # breakeven+ stop after partial
                stop_p = max(stop_p, entry_p * (1.0 + 0.0015))

            # Unit2 trailing after partial
            if unit1_done and qty_open > 0:
                if math.isfinite(a15) and a15 > 0:
                    trail = high_pk - cand.trail_mult * a15
                    stop_p = max(stop_p, trail)
                if lo <= stop_p:
                    leg = qty_open * ((stop_p - entry_p) / entry_p)
                    pnl = realized + cost_adj(leg, qty_open)
                    equity *= 1.0 + pnl
                    in_pos = False
            continue

        if pending:
            if hi >= pend_stop:
                entry_p = pend_stop
                stop_p = entry_p - pend_risk
                unit1_tp = entry_p + cand.tp_rr * pend_risk
                qty_open = 1.0
                unit1_done = False
                high_pk = hi
                realized = 0.0
                be_moved = False
                pl_moved = False
                in_pos = True
                pending = False
            else:
                f5 = arr.fast5[i]
                s5 = arr.slow5[i]
                if math.isfinite(f5) and f5 > s5:
                    pend_stop = min(pend_stop, hi)
                else:
                    pending = False
            continue

        if not arr.long_sig[i] or arr.blocked[i]:
            continue
        if day_trade_cnt.get(day, 0) >= MAX_TRADES_PER_DAY:
            continue
        a5 = arr.atr5[i]
        if not (math.isfinite(a5) and a5 > 0):
            continue
        risk = cand.atr_stop * a5
        pending = True
        pend_stop = arr.high[i]
        pend_risk = risk
        day_trade_cnt[day] = day_trade_cnt.get(day, 0) + 1

    if in_pos:
        cl = arr.close[n - 1]
        leg = qty_open * ((cl - entry_p) / entry_p)
        pnl = realized + cost_adj(leg, qty_open)
        equity *= 1.0 + pnl

    return (equity - 1.0) * 100.0


def _sim_atr(arr: SymArrays, cand: Candidate, fee_r: float, slip_r: float) -> float:
    """
    ATR mode: 2% risk sizing, full exit at stop or target. Unchanged.
    Returns total return %.
    """
    n = arr.n
    capital = 10_000.0
    risk_pct = 0.02
    day_trade_cnt: dict[int, int] = {}

    in_pos = False
    entry_p = stop_p = target_p = qty = risk_d = 0.0
    be_done = False
    high_pk = 0.0

    for i in range(2, n):
        hi = arr.high[i]
        lo = arr.low[i]
        cl = arr.close[i]
        a15 = arr.atr15[i]
        day = int(arr.day_idx[i])

        if in_pos:
            high_pk = max(high_pk, hi)
            if not be_done and hi >= entry_p + cand.be_r * risk_d:
                stop_p = max(stop_p, entry_p)
                be_done = True
            if cand.lock_trigger > 0 and hi >= entry_p * (1.0 + cand.lock_trigger):
                stop_p = max(stop_p, entry_p * (1.0 + cand.lock_stop))
            if be_done and math.isfinite(a15) and a15 > 0:
                stop_p = max(stop_p, high_pk - cand.trail_mult * a15)
            exit_p = 0.0
            if lo <= stop_p:
                exit_p = stop_p
            elif hi >= target_p:
                exit_p = target_p
            if exit_p > 0:
                ee = entry_p * (1.0 + slip_r)
                xe = exit_p * (1.0 - slip_r)
                pnl_eur = (xe - ee) * qty - fee_r * (ee + xe) * qty
                capital += pnl_eur
                in_pos = False
            continue

        if not arr.long_sig[i] or arr.blocked[i]:
            continue
        if day_trade_cnt.get(day, 0) >= MAX_TRADES_PER_DAY:
            continue
        a5 = arr.atr5[i]
        if not (math.isfinite(a5) and a5 > 0):
            continue
        risk_d = cand.atr_stop * a5
        entry_p = cl
        stop_p = cl - risk_d
        target_p = cl + cand.tp_rr * risk_d
        qty = capital * risk_pct / risk_d
        if qty <= 0:
            continue
        be_done = False
        high_pk = hi
        in_pos = True
        day_trade_cnt[day] = day_trade_cnt.get(day, 0) + 1

    if in_pos:
        cl = arr.close[n - 1]
        ee = entry_p * (1.0 + slip_r)
        xe = cl * (1.0 - slip_r)
        pnl_eur = (xe - ee) * qty - fee_r * (ee + xe) * qty
        capital += pnl_eur

    return (capital / 10_000.0 - 1.0) * 100.0


def _portfolio_return(arrs: dict[str, SymArrays], cand: Candidate) -> float:
    rets = []
    for sym, arr in arrs.items():
        fee_r = _fee_bps_per_side_for_symbol(sym) / 10_000.0
        slip_r = SLIPPAGE_BPS / 10_000.0
        if SYMBOL_MODE_MAP.get(sym, "BASE") == "ATR":
            rets.append(_sim_atr(arr, cand, fee_r, slip_r))
        else:
            rets.append(_sim_base(arr, cand, fee_r, slip_r))
    return float(np.mean(rets)) if rets else 0.0


def main() -> None:
    params = StrategyParams()
    # Use current live parameters
    base = Candidate(
        label="CURRENT",
        atr_stop=float(params.atr_multiplier),
        tp_rr=float(params.unit1_tp_rr),
        be_r=float(params.atr_dynamic_be_r),
        be_pct=float(params.break_even_trigger_pct),
        trail_mult=float(params.atr_trail_mult),
        lock_trigger=float(params.profit_lock_trigger_pct),
        lock_stop=float(params.profit_lock_stop_pct),
        trail_in_unit1=False,
    )
    exp = Candidate(**{**base.__dict__, "label": "UNIT1_TRAIL", "trail_in_unit1": True})

    files = _discover_symbol_files(DATA_DIR)
    proc: dict[str, SymArrays] = {}
    min_ts = None
    max_ts = None

    for sym in SYMBOLS:
        f = files.get(sym)
        if not f:
            continue
        df = pd.read_csv(f)
        ts_col = "timestamp" if "timestamp" in df.columns else next(
            (c for c in df.columns if "time" in c.lower() or "date" in c.lower()), None
        )
        if not ts_col:
            continue
        df[ts_col] = pd.to_datetime(df[ts_col], utc=True, errors="coerce")
        df = df.dropna(subset=[ts_col]).sort_values(ts_col).set_index(ts_col)
        df.columns = [c.lower() for c in df.columns]
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        if len(df) < 200:
            continue

        dfp = add_indicators(df, ema_period=EMA_PERIOD).dropna()
        proc[sym] = _precompute(dfp)
        min_ts = dfp.index.min() if min_ts is None else min(min_ts, dfp.index.min())
        max_ts = dfp.index.max() if max_ts is None else max(max_ts, dfp.index.max())

    if not proc:
        print("No data available.")
        return

    print("=== UNIT1 trailing experiment (max available history) ===")
    print(f"History used: {min_ts.date()} -> {max_ts.date()} (5m bars, per-symbol CSVs)")
    print(f"Slippage: {SLIPPAGE_BPS} bps | Fees: per-symbol BG/T212 model")
    print()
    print(f"Params: atr_stop={base.atr_stop} tp_rr={base.tp_rr} be_r={base.be_r} be_pct={base.be_pct} trail_mult={base.trail_mult} lock={base.lock_trigger}/{base.lock_stop}")
    print()

    cur = _portfolio_return(proc, base)
    alt = _portfolio_return(proc, exp)
    print(f"PORTFOLIO AVG return (current):     {cur:+.2f}%")
    print(f"PORTFOLIO AVG return (unit1 trail): {alt:+.2f}%")
    print(f"Delta: {alt-cur:+.2f}%")

    print()
    print("Per-symbol returns:")
    for sym, arr in proc.items():
        fee_r = _fee_bps_per_side_for_symbol(sym) / 10_000.0
        slip_r = SLIPPAGE_BPS / 10_000.0
        if SYMBOL_MODE_MAP.get(sym, "BASE") == "ATR":
            r1 = _sim_atr(arr, base, fee_r, slip_r)
            r2 = _sim_atr(arr, exp, fee_r, slip_r)
        else:
            r1 = _sim_base(arr, base, fee_r, slip_r)
            r2 = _sim_base(arr, exp, fee_r, slip_r)
        print(f"  {sym:<7} {SYMBOL_MODE_MAP.get(sym,'BASE'):<4} current={r1:+8.2f}%  unit1trail={r2:+8.2f}%  delta={r2-r1:+8.2f}%")


if __name__ == "__main__":
    main()

