"""
T212 Live Strategy Upgrade Lab
================================
Uses ENGINE A logic (real live-bot capital model) but with vectorized
NumPy inner loops for speed.

Architecture
------------
- Pre-compute indicators once per symbol (expensive pandas ops done once)
- Extract all needed arrays to NumPy before the grid sweep
- Inner simulation loop: pure Python + NumPy array indexing (~100x faster)
- Three OOS windows (IS 2024H1, OOS1 2024H2, OOS2 2025-2026)
- Score = OOS_avg - 0.5*|OOS1-OOS2| + 0.1*IS
- Bulgaria/T212 cost model (FX, stamp duty, 10 bps slippage)
- Reports full 2yr profit for winner and current config
"""
from __future__ import annotations

import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from t212_miner_bot.backtests.t212_bulgaria_fee_tax_portfolio_test import (
    _discover_symbol_files,
    _fee_bps_per_side_for_symbol,
)
from t212_miner_bot.config import StrategyParams
from t212_miner_bot.indicators import add_indicators

# ─────────────────────────────────────────────────────────────────────────────
DATA_DIR = REPO_ROOT / "data"
SLIPPAGE_BPS = 10.0
MAX_TRADES_PER_DAY = 2
EMA_PERIOD = 200

SYMBOLS = ["ASML.AS", "SAP.DE", "UNA.AS", "AMD"]
# ATR mode: full-capital 2% risk sizing, single TP target
# BASE mode: full-equity unit1/unit2 split, trailing runner
SYMBOL_MODE_MAP = {"ASML.AS": "BASE", "SAP.DE": "ATR", "UNA.AS": "BASE", "AMD": "BASE"}

IS_START   = pd.Timestamp("2024-01-01", tz="UTC")
IS_END     = pd.Timestamp("2024-06-30", tz="UTC")
OOS1_START = pd.Timestamp("2024-07-01", tz="UTC")
OOS1_END   = pd.Timestamp("2024-12-31", tz="UTC")
OOS2_START = pd.Timestamp("2025-01-01", tz="UTC")
OOS2_END   = pd.Timestamp("2026-04-01", tz="UTC")
FULL_START = pd.Timestamp("2024-01-01", tz="UTC")
FULL_END   = pd.Timestamp("2026-04-01", tz="UTC")

WINDOWS = [
    ("IS",   IS_START,   IS_END),
    ("OOS1", OOS1_START, OOS1_END),
    ("OOS2", OOS2_START, OOS2_END),
]

_P = StrategyParams()


# ─────────────────────────────────────────────────────────────────────────────
# Candidate
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Candidate:
    label: str
    atr_stop: float       # ATR multiple for initial stop distance
    tp_rr: float          # take-profit in R (BASE: unit1 TP; ATR: full exit)
    be_r: float           # break-even trigger in R (ATR mode)
    be_pct: float         # break-even trigger % (BASE mode)
    trail_mult: float     # ATR trailing stop mult after BE
    lock_trigger: float   # profit-lock trigger % (0 = disabled)
    lock_stop: float      # profit-lock stop % (when lock_trigger hit)
    entry_filter: str     # NONE | TREND | PULLBACK_EMA | COMPRESSION | BREAKOUT_ATR
    entry_param: float    # parameter for filter


def _baseline() -> Candidate:
    return Candidate(
        label="CURRENT",
        atr_stop=float(_P.atr_multiplier),
        tp_rr=float(_P.unit1_tp_rr),
        be_r=float(_P.atr_dynamic_be_r),
        be_pct=float(_P.break_even_trigger_pct),
        trail_mult=float(_P.atr_trail_mult),
        lock_trigger=float(_P.profit_lock_trigger_pct),
        lock_stop=float(_P.profit_lock_stop_pct),
        entry_filter="TREND",
        entry_param=0.0,
    )


def _build_grid() -> list[Candidate]:
    cands: list[Candidate] = [_baseline()]
    seen: set[tuple] = set()

    def _add(c: Candidate) -> None:
        key = (
            round(c.atr_stop, 3), round(c.tp_rr, 3),
            round(c.be_r, 3), round(c.be_pct, 4),
            round(c.trail_mult, 3),
            round(c.lock_trigger, 5), round(c.lock_stop, 5),
            c.entry_filter, round(c.entry_param, 3),
        )
        if key not in seen:
            seen.add(key)
            cands.append(c)

    # ── Core ATR/TP/BE/trail grid with entry filter
    for atr_stop in [2.0, 2.5, 3.0, 3.5]:
        for tp_rr in [4.0, 5.0, 6.0, 7.0, 8.0]:
            if tp_rr <= atr_stop:
                continue
            for be_r in [1.5, 2.0, 2.5]:
                for trail in [1.5, 2.0, 2.5]:
                    for lock_t, lock_s in [
                        (0.034, 0.014),
                        (0.05, 0.020),
                        (0.0, 0.0),
                    ]:
                        for ef in ["NONE", "TREND"]:
                            lbl = f"s{atr_stop}_tp{tp_rr}_be{be_r}_tr{trail}_lt{lock_t}_{ef}"
                            _add(Candidate(
                                label=lbl,
                                atr_stop=atr_stop, tp_rr=tp_rr,
                                be_r=be_r, be_pct=0.02,
                                trail_mult=trail,
                                lock_trigger=lock_t, lock_stop=lock_s,
                                entry_filter=ef, entry_param=0.0,
                            ))

    # ── Pullback EMA filter
    for atr_stop in [2.5, 3.0]:
        for tp_rr in [5.0, 6.0, 7.0]:
            if tp_rr <= atr_stop:
                continue
            for param in [2.0, 3.0, 4.0]:
                _add(Candidate(
                    label=f"s{atr_stop}_tp{tp_rr}_PULLBACK{param}",
                    atr_stop=atr_stop, tp_rr=tp_rr,
                    be_r=2.0, be_pct=0.02,
                    trail_mult=2.0,
                    lock_trigger=0.034, lock_stop=0.014,
                    entry_filter="PULLBACK_EMA", entry_param=param,
                ))

    # ── Compression-break filter
    for atr_stop in [2.5, 3.0]:
        for tp_rr in [5.0, 6.0]:
            if tp_rr <= atr_stop:
                continue
            for param in [3.5, 4.5, 5.5]:
                _add(Candidate(
                    label=f"s{atr_stop}_tp{tp_rr}_COMP{param}",
                    atr_stop=atr_stop, tp_rr=tp_rr,
                    be_r=2.0, be_pct=0.02,
                    trail_mult=2.0,
                    lock_trigger=0.034, lock_stop=0.014,
                    entry_filter="COMPRESSION", entry_param=param,
                ))

    # ── Breakout ATR buffer
    for atr_stop in [2.5, 3.0]:
        for tp_rr in [5.0, 6.0, 7.0]:
            if tp_rr <= atr_stop:
                continue
            for param in [0.3, 0.5, 0.7]:
                _add(Candidate(
                    label=f"s{atr_stop}_tp{tp_rr}_BO{param}",
                    atr_stop=atr_stop, tp_rr=tp_rr,
                    be_r=2.0, be_pct=0.02,
                    trail_mult=2.0,
                    lock_trigger=0.034, lock_stop=0.014,
                    entry_filter="BREAKOUT_ATR", entry_param=param,
                ))

    return cands


# ─────────────────────────────────────────────────────────────────────────────
# Pre-compute signal arrays  (once per symbol/window)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SymArrays:
    n: int
    close:   np.ndarray
    high:    np.ndarray
    low:     np.ndarray
    atr5:    np.ndarray
    atr15:   np.ndarray
    ema15:   np.ndarray
    fast5:   np.ndarray
    slow5:   np.ndarray
    fast15:  np.ndarray
    slow15:  np.ndarray
    vol_ma20:np.ndarray
    # pre-computed signal masks (True where condition holds)
    long_sig: np.ndarray   # regime_long AND long_trigger (DTosc crossup)
    blocked:  np.ndarray   # time-blocked (lunch / EU open buffer)
    days:     np.ndarray   # integer day index per bar (for trade-count gate)
    day_idx:  np.ndarray   # unique day id (same date -> same int)


def _precompute(df: pd.DataFrame) -> SymArrays:
    """Extract all arrays needed for inner simulation loop."""
    n = len(df)
    close  = df["close"].to_numpy(dtype=float)
    high   = df["high"].to_numpy(dtype=float)
    low    = df["low"].to_numpy(dtype=float)
    atr5   = df["atr_5m"].to_numpy(dtype=float)
    atr15  = df["atr_15m"].to_numpy(dtype=float)
    ema15  = df["ema_15m"].to_numpy(dtype=float)
    fast5  = df["fast_5m"].to_numpy(dtype=float)
    slow5  = df["slow_5m"].to_numpy(dtype=float)
    fast15 = df["fast_15m"].to_numpy(dtype=float)
    slow15 = df["slow_15m"].to_numpy(dtype=float)

    # Volume MA20 for volume-spike filter (may not exist)
    if "volume" in df.columns:
        vol = df["volume"].to_numpy(dtype=float)
        vol_ma20 = np.full(n, float("nan"))
        for i in range(20, n):
            vol_ma20[i] = np.mean(vol[i - 20:i])
    else:
        vol_ma20 = np.full(n, float("nan"))

    # Long signal: regime (15m) + trigger (5m DTosc cross-up), overbought guard
    long_sig = np.zeros(n, dtype=bool)
    for i in range(2, n):
        if not (math.isfinite(ema15[i]) and math.isfinite(fast15[i]) and math.isfinite(fast5[i])):
            continue
        regime_long  = (close[i] > ema15[i]) and (fast15[i] > slow15[i]) and (fast15[i] < 75.0)
        long_trigger = (fast5[i - 1] <= slow5[i - 1]) and (fast5[i] > slow5[i]) and (fast5[i] < 75.0)
        long_sig[i] = regime_long and long_trigger

    # Blocked bars (lunch 12:00-12:30 CET, EU open buffer 09:00-09:15 CET)
    blocked = np.zeros(n, dtype=bool)
    for i, ts in enumerate(df.index):
        # Convert to CET (UTC+1 standard, UTC+2 DST) – approximate with UTC+1
        local_h = ts.hour + 1  # rough CET
        local_m = ts.minute
        # Lunch: 11:55-12:35 UTC (≈12:55-13:35 CET) -- use what OOS backtest uses
        if (ts.hour == 11 and ts.minute >= 55) or (ts.hour == 12 and ts.minute <= 35):
            blocked[i] = True
        # EU open buffer: 07:55-08:15 UTC (≈08:55-09:15 CET)
        if ts.hour == 7 and ts.minute >= 55:
            blocked[i] = True
        if ts.hour == 8 and ts.minute <= 15:
            blocked[i] = True

    # Day index (integer per unique date)
    dates = np.array([ts.date() for ts in df.index])
    unique_days, day_idx = np.unique(dates, return_inverse=True)

    return SymArrays(
        n=n, close=close, high=high, low=low,
        atr5=atr5, atr15=atr15, ema15=ema15,
        fast5=fast5, slow5=slow5, fast15=fast15, slow15=slow15,
        vol_ma20=vol_ma20,
        long_sig=long_sig, blocked=blocked,
        days=dates, day_idx=day_idx,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Fast simulation kernels (pure Python + NumPy indexing, no pandas inside)
# ─────────────────────────────────────────────────────────────────────────────

def _entry_ok(arr: SymArrays, i: int, ef: str, ep: float) -> bool:
    """Additional entry quality filters beyond DTosc signal."""
    if ef in ("", "NONE"):
        return True
    if ef == "TREND":
        # 15m EMA slope up AND 15m DTosc bullish
        if i < 2:
            return False
        e15 = arr.ema15[i]
        e15p = arr.ema15[i - 1]
        f15  = arr.fast15[i]
        s15  = arr.slow15[i]
        if not (math.isfinite(e15) and math.isfinite(e15p)):
            return False
        return (e15 > e15p) and (f15 > s15)
    a5 = arr.atr5[i]
    if not (math.isfinite(a5) and a5 > 0):
        return False
    cl = arr.close[i]
    if ef == "PULLBACK_EMA":
        # close within ep*ATR above EMA15
        e15 = arr.ema15[i]
        if not math.isfinite(e15):
            return False
        return cl > e15 and (cl - e15) <= ep * a5
    if ef == "BREAKOUT_ATR":
        if i < 1:
            return False
        ph = arr.high[i - 1]
        return cl > ph + ep * a5
    if ef == "COMPRESSION":
        window = 8
        if i < window:
            return False
        rng = arr.high[i - window:i].max() - arr.low[i - window:i].min()
        return (rng / a5) <= ep and cl > arr.high[i - 1]
    return True


def _sim_base(arr: SymArrays, cand: Candidate, fee_r: float, slip_r: float) -> tuple[float, int, float]:
    """
    BASE mode: unit1 (50%) exits at close >= unit1_tp; unit2 trails.
    Returns (total_return_pct, n_trades, win_rate_pct).
    Capital model: equity multiplier (same as Engine A).
    """
    n = arr.n
    equity = 1.0
    trades: list[float] = []
    day_trade_cnt: dict[Any, int] = {}

    # position state
    in_pos  = False
    pending = False
    pend_stop = 0.0
    pend_risk = 0.0

    entry_p   = 0.0
    stop_p    = 0.0
    unit1_tp  = 0.0
    qty_open  = 0.0         # fraction of equity
    unit1_done= False
    high_pk   = 0.0
    realized  = 0.0
    be_moved  = False

    for i in range(2, n):
        hi  = arr.high[i]
        lo  = arr.low[i]
        cl  = arr.close[i]
        a15 = arr.atr15[i]
        day = arr.day_idx[i]

        # ── manage position ──────────────────────────────────────────────────
        if in_pos:
            # Break-even
            if not be_moved and hi >= entry_p * (1.0 + cand.be_pct):
                stop_p = max(stop_p, entry_p)
                be_moved = True

            # Profit lock
            if cand.lock_trigger > 0 and hi >= entry_p * (1.0 + cand.lock_trigger):
                stop_p = max(stop_p, entry_p * (1.0 + cand.lock_stop))

            # Stop hit
            if lo <= stop_p:
                leg = qty_open * ((stop_p - entry_p) / entry_p)
                leg_net = leg * (1.0 - fee_r) - slip_r * 2 * qty_open
                pnl = realized + leg_net
                equity *= 1.0 + pnl
                trades.append(pnl)
                in_pos = False
                continue

            # Unit1 TP
            if not unit1_done and cl >= unit1_tp:
                half = 0.5
                raw = half * ((cl - entry_p) / entry_p)
                realized += raw * (1.0 - fee_r) - slip_r * 2 * half
                qty_open -= half
                unit1_done = True
                stop_p = max(stop_p, entry_p * (1.0 + 0.0015))

            # Unit2 trail
            if unit1_done and qty_open > 0:
                high_pk = max(high_pk, hi)
                if math.isfinite(a15) and a15 > 0:
                    trail = high_pk - cand.trail_mult * a15
                    stop_p = max(stop_p, trail)
                if lo <= stop_p:
                    leg = qty_open * ((stop_p - entry_p) / entry_p)
                    leg_net = leg * (1.0 - fee_r) - slip_r * 2 * qty_open
                    pnl = realized + leg_net
                    equity *= 1.0 + pnl
                    trades.append(pnl)
                    in_pos = False
                continue

            continue

        # ── pending entry ────────────────────────────────────────────────────
        if pending:
            if hi >= pend_stop:
                entry_p  = pend_stop
                stop_p   = entry_p - pend_risk
                unit1_tp = entry_p + cand.tp_rr * pend_risk
                qty_open = 1.0
                unit1_done = False
                high_pk    = hi
                realized   = 0.0
                be_moved   = False
                in_pos     = True
                pending    = False
            else:
                f5  = arr.fast5[i]
                s5  = arr.slow5[i]
                if math.isfinite(f5) and f5 > s5:
                    pend_stop = min(pend_stop, hi)
                else:
                    pending = False
            continue

        # ── new signal ────────────────────────────────────────────────────────
        if not arr.long_sig[i]:
            continue
        if arr.blocked[i]:
            continue
        if not _entry_ok(arr, i, cand.entry_filter, cand.entry_param):
            continue
        cnt = day_trade_cnt.get(day, 0)
        if cnt >= MAX_TRADES_PER_DAY:
            continue

        a5 = arr.atr5[i]
        if not (math.isfinite(a5) and a5 > 0):
            continue

        risk = cand.atr_stop * a5
        pending    = True
        pend_stop  = arr.high[i]
        pend_risk  = risk
        day_trade_cnt[day] = cnt + 1

    # Close open position at end
    if in_pos:
        cl = arr.close[n - 1]
        leg = qty_open * ((cl - entry_p) / entry_p)
        leg_net = leg * (1.0 - fee_r) - slip_r * 2 * qty_open
        pnl = realized + leg_net
        equity *= 1.0 + pnl
        trades.append(pnl)

    total = len(trades)
    win_r = sum(1 for p in trades if p > 0) / total * 100.0 if total else 0.0
    return (equity - 1.0) * 100.0, total, win_r


def _sim_atr(arr: SymArrays, cand: Candidate, fee_r: float, slip_r: float) -> tuple[float, int, float]:
    """
    ATR mode: 2% risk-per-trade sizing, single entry at close, single TP exit.
    Returns (total_return_pct, n_trades, win_rate_pct).
    """
    n = arr.n
    capital = 10_000.0
    risk_pct = 0.02
    trades: list[float] = []
    day_trade_cnt: dict[Any, int] = {}

    in_pos   = False
    entry_p  = 0.0
    stop_p   = 0.0
    target_p = 0.0
    qty      = 0.0
    risk_d   = 0.0
    be_done  = False
    high_pk  = 0.0

    for i in range(2, n):
        hi  = arr.high[i]
        lo  = arr.low[i]
        cl  = arr.close[i]
        a15 = arr.atr15[i]
        day = arr.day_idx[i]

        if in_pos:
            high_pk = max(high_pk, hi)

            # Break-even (R-multiple)
            if not be_done and hi >= entry_p + cand.be_r * risk_d:
                stop_p = max(stop_p, entry_p)
                be_done = True

            # Profit lock
            if cand.lock_trigger > 0 and entry_p > 0 and hi >= entry_p * (1.0 + cand.lock_trigger):
                stop_p = max(stop_p, entry_p * (1.0 + cand.lock_stop))

            # ATR trail after BE
            if be_done and math.isfinite(a15) and a15 > 0:
                trail = high_pk - cand.trail_mult * a15
                stop_p = max(stop_p, trail)

            exit_p = 0.0
            if lo <= stop_p:
                exit_p = stop_p
            elif hi >= target_p:
                exit_p = target_p

            if exit_p > 0:
                ee = entry_p * (1.0 + slip_r)
                xe = exit_p  * (1.0 - slip_r)
                pnl = (xe - ee) * qty - fee_r * (ee + xe) * qty
                capital += pnl
                trades.append(pnl)
                in_pos = False
            continue

        # New signal
        if not arr.long_sig[i]:
            continue
        if arr.blocked[i]:
            continue
        if not _entry_ok(arr, i, cand.entry_filter, cand.entry_param):
            continue
        cnt = day_trade_cnt.get(day, 0)
        if cnt >= MAX_TRADES_PER_DAY:
            continue

        a5 = arr.atr5[i]
        if not (math.isfinite(a5) and a5 > 0):
            continue

        risk_d = cand.atr_stop * a5
        if risk_d <= 0:
            continue

        entry_p  = cl
        stop_p   = cl - risk_d
        target_p = cl + cand.tp_rr * risk_d
        qty      = capital * risk_pct / risk_d
        if qty <= 0:
            continue
        be_done  = False
        high_pk  = hi
        in_pos   = True
        day_trade_cnt[day] = cnt + 1

    # Close at end
    if in_pos:
        cl = arr.close[n - 1]
        ee = entry_p * (1.0 + slip_r)
        xe = cl * (1.0 - slip_r)
        pnl = (xe - ee) * qty - fee_r * (ee + xe) * qty
        capital += pnl
        trades.append(pnl)

    total = len(trades)
    win_r = sum(1 for p in trades if p > 0) / total * 100.0 if total else 0.0
    return (capital / 10_000.0 - 1.0) * 100.0, total, win_r


def _sim(arr: SymArrays, symbol: str, cand: Candidate) -> tuple[float, int, float]:
    """Dispatch to BASE or ATR kernel."""
    fee_bps = _fee_bps_per_side_for_symbol(symbol)
    fee_r   = fee_bps / 10_000.0
    slip_r  = SLIPPAGE_BPS / 10_000.0
    mode = SYMBOL_MODE_MAP.get(symbol, "BASE")
    if mode == "ATR":
        return _sim_atr(arr, cand, fee_r, slip_r)
    return _sim_base(arr, cand, fee_r, slip_r)


def _portfolio_return(win_arrays: dict[str, SymArrays], cand: Candidate) -> float:
    rets = [_sim(arr, sym, cand)[0] for sym, arr in win_arrays.items()]
    return sum(rets) / len(rets) if rets else 0.0


def _score(is_r: float, oos1_r: float, oos2_r: float) -> float:
    oos_avg = (oos1_r + oos2_r) / 2.0
    oos_vol = abs(oos1_r - oos2_r) / 2.0
    return oos_avg - 0.5 * oos_vol + 0.1 * is_r


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def run() -> None:
    print("=" * 72)
    print("T212 LIVE STRATEGY UPGRADE LAB (Engine A-NumPy)")
    print("IS=2024H1 | OOS1=2024H2 | OOS2=2025+ | BG/T212 costs")
    print("=" * 72)

    files = _discover_symbol_files(DATA_DIR)
    full_dfs: dict[str, pd.DataFrame] = {}
    for sym in SYMBOLS:
        if sym not in files:
            print(f"[WARN] No CSV for {sym}")
            continue
        df = pd.read_csv(files[sym])
        needed = {"timestamp", "open", "high", "low", "close", "volume"}
        if not needed.issubset(df.columns):
            print(f"[WARN] Bad columns {sym}")
            continue
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        df = df.dropna(subset=["timestamp", "open", "high", "low", "close"]).sort_values("timestamp")
        df = df.set_index("timestamp")
        full_dfs[sym] = df
        print(f"[DATA] {sym}: {len(df)} bars  {df.index[0].date()} -> {df.index[-1].date()}")

    if not full_dfs:
        print("No data. Aborting.")
        return

    # Pre-compute indicators once per symbol
    print("\nPre-computing indicators (once per symbol)...")
    proc_dfs: dict[str, pd.DataFrame] = {}
    for sym, df in full_dfs.items():
        p = add_indicators(df, ema_period=EMA_PERIOD).dropna()
        proc_dfs[sym] = p
        print(f"  {sym}: {len(p)} processed bars")

    # Pre-compute SymArrays for each window
    print("\nPre-computing signal arrays per window...")
    win_arrays: dict[str, dict[str, SymArrays]] = {}
    for wname, ws, we in WINDOWS:
        win_arrays[wname] = {}
        for sym, df in proc_dfs.items():
            sliced = df[(df.index >= ws) & (df.index <= we)]
            if len(sliced) >= 50:
                win_arrays[wname][sym] = _precompute(sliced)
                print(f"  {wname} {sym}: {len(sliced)} bars")

    # Pre-compute full 2yr arrays
    full_arrays: dict[str, SymArrays] = {}
    for sym, df in proc_dfs.items():
        sliced = df[(df.index >= FULL_START) & (df.index <= FULL_END)]
        if len(sliced) >= 50:
            full_arrays[sym] = _precompute(sliced)

    cands = _build_grid()
    total = len(cands)
    print(f"\nGrid: {total} candidates x {len(full_dfs)} symbols x 3 windows")
    print("Running sweep...\n")

    results: list[tuple[float, float, float, float, Candidate]] = []
    t0 = time.time()
    for idx, cand in enumerate(cands):
        if idx == 20:
            elapsed = time.time() - t0
            est = elapsed / 20 * total / 60
            print(f"  Speed estimate: ~{est:.0f} min total", flush=True)
        if idx % 200 == 0 and idx > 0:
            elapsed = time.time() - t0
            remaining = elapsed / idx * (total - idx) / 60
            print(f"  [{idx}/{total}]  ~{remaining:.1f} min remaining", flush=True)

        is_r   = _portfolio_return(win_arrays.get("IS",   {}), cand)
        oos1_r = _portfolio_return(win_arrays.get("OOS1", {}), cand)
        oos2_r = _portfolio_return(win_arrays.get("OOS2", {}), cand)
        sc = _score(is_r, oos1_r, oos2_r)
        results.append((sc, is_r, oos1_r, oos2_r, cand))

    elapsed_total = time.time() - t0
    print(f"\nSweep done in {elapsed_total/60:.1f} min ({elapsed_total:.0f}s)")

    results.sort(key=lambda x: -x[0])

    current_entry = next((r for r in results if r[4].label == "CURRENT"), None)
    c_sc = c_is = c_oos1 = c_oos2 = 0.0
    if current_entry:
        c_sc, c_is, c_oos1, c_oos2, _ = current_entry

    print(f"\n{'RANK':<5} {'SCORE':>8} {'IS%':>8} {'OOS1%':>8} {'OOS2%':>8}  BEAT   LABEL")
    print("-" * 90)

    winner: Candidate | None = None
    winner_data: tuple | None = None
    for rank, (sc, is_r, oos1_r, oos2_r, cand) in enumerate(results[:30], 1):
        beat = ("BOTH" if (oos1_r > c_oos1 and oos2_r > c_oos2)
                else ("OOS1" if oos1_r > c_oos1 else ("OOS2" if oos2_r > c_oos2 else "    ")))
        tag = " <- CURRENT" if cand.label == "CURRENT" else ""
        print(f"  {rank:<3} {sc:>8.2f} {is_r:>8.2f} {oos1_r:>8.2f} {oos2_r:>8.2f}  {beat}   {cand.label}{tag}")
        if winner is None and cand.label != "CURRENT" and beat == "BOTH":
            winner = cand
            winner_data = (sc, is_r, oos1_r, oos2_r)

    if winner is None:
        # Pick best by score regardless
        for sc, is_r, oos1_r, oos2_r, cand in results:
            if cand.label != "CURRENT":
                winner = cand
                winner_data = (sc, is_r, oos1_r, oos2_r)
                break

    print("\n" + "=" * 72)
    print("CURRENT CONFIG SUMMARY:")
    print(f"  Score={c_sc:.2f}  IS={c_is:.2f}%  OOS1={c_oos1:.2f}%  OOS2={c_oos2:.2f}%")

    if winner and winner_data:
        wsc, wis, woos1, woos2 = winner_data
        print(f"\nWINNER: {winner.label}")
        print(f"  Score={wsc:.2f}  IS={wis:.2f}%  OOS1={woos1:.2f}%  OOS2={woos2:.2f}%")
        print(f"  vs current: Dscore={wsc-c_sc:+.2f}  DOIS1={woos1-c_oos1:+.2f}%  DOIS2={woos2-c_oos2:+.2f}%")

        print("\n--- WINNER PARAMETERS ---")
        print(f"  atr_stop       = {winner.atr_stop}")
        print(f"  tp_rr          = {winner.tp_rr}")
        print(f"  be_r (ATR)     = {winner.be_r}")
        print(f"  be_pct (BASE)  = {winner.be_pct}")
        print(f"  trail_mult     = {winner.trail_mult}")
        print(f"  lock_trigger   = {winner.lock_trigger}")
        print(f"  lock_stop      = {winner.lock_stop}")
        print(f"  entry_filter   = {winner.entry_filter}  param={winner.entry_param}")

        # Full 2yr portfolio return
        print("\n" + "=" * 72)
        print(f"FULL 2-YEAR PORTFOLIO RETURN (2024-01 to 2026-04)")
        print(f"[Engine A-NumPy | BG/T212 costs | {SLIPPAGE_BPS}bps slippage]")
        print("=" * 72)
        baseline = _baseline()
        print(f"\n  {'Symbol':<12} {'CURRENT%':>10} {'WINNER%':>10} {'Delta%':>10}  T(W)  WR(W)")
        print("  " + "-" * 60)
        p_cur, p_win = [], []
        for sym in SYMBOLS:
            arr = full_arrays.get(sym)
            if arr is None:
                continue
            rc, tc, wrc = _sim(arr, sym, baseline)
            rw, tw, wrw = _sim(arr, sym, winner)
            p_cur.append(rc)
            p_win.append(rw)
            d = rw - rc
            print(f"  {sym:<12} {rc:>+10.2f}% {rw:>+10.2f}% {d:>+10.2f}%  {tw:>4}  {wrw:>5.1f}%")
        pc = sum(p_cur) / len(p_cur) if p_cur else 0.0
        pw = sum(p_win) / len(p_win) if p_win else 0.0
        print("  " + "-" * 60)
        print(f"  {'PORTFOLIO':<12} {pc:>+10.2f}% {pw:>+10.2f}% {pw-pc:>+10.2f}%")
        print()
        print(f"  *** CURRENT real 2yr profit:  {pc:+.2f}% (avg per symbol) ***")
        print(f"  *** WINNER  real 2yr profit:  {pw:+.2f}% (avg per symbol) ***")
        print(f"  *** Improvement:             {pw-pc:+.2f}% ***")
        print()

    print("=" * 72)
    print("Done.")


if __name__ == "__main__":
    run()
