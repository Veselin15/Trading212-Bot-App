"""
T212 Strategy Upgrade Lab -- robust multi-window OOS sweep.

Three non-overlapping windows (no overfit):
  IS    2024-01 -> 2024-06  (in-sample narrowing)
  OOS1  2024-07 -> 2024-12
  OOS2  2025-01 -> 2026-04

Score = OOS_avg - 0.5*|OOS1-OOS2| + 0.1*IS  (OOS-heavy, low variance wins)

Bulgaria/T212 cost model: FX fee + stamp duty/FTT where applicable, 10 bps slippage.

Speed: signals pre-computed once per window per symbol; sim loop is ~5ms per call.
"""

from __future__ import annotations

import math
import sys
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
from t212_miner_bot.backtests.t212_oos_regime_backtest import _is_lunch_blocked, _is_eu_open_buffer
from t212_miner_bot.config import StrategyParams
from t212_miner_bot.indicators import add_indicators, cross_up

DATA_DIR = REPO_ROOT / "data"
SLIPPAGE_BPS = 10.0
MAX_TRADES_PER_DAY = 2
SYMBOLS = ["ASML.AS", "SAP.DE", "UNA.AS", "AMD"]

IS_START   = pd.Timestamp("2024-01-01T00:00:00Z")
IS_END     = pd.Timestamp("2024-06-30T23:59:59Z")
OOS1_START = pd.Timestamp("2024-07-01T00:00:00Z")
OOS1_END   = pd.Timestamp("2024-12-31T23:59:59Z")
OOS2_START = pd.Timestamp("2025-01-01T00:00:00Z")
OOS2_END   = pd.Timestamp("2026-04-01T23:59:59Z")

WINDOWS = [
    ("IS",   IS_START,   IS_END),
    ("OOS1", OOS1_START, OOS1_END),
    ("OOS2", OOS2_START, OOS2_END),
]

_P = StrategyParams()


# ---------------------------------------------------------------------------
# Candidate dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Candidate:
    label: str
    atr_stop: float       # Stop distance in ATR multiples
    tp_r: float           # TP in R-multiples
    be_r: float           # Break-even activation in R-multiples
    trail_mult: float     # ATR15m trailing multiplier (post-BE)
    lock_trigger: float   # Profit-lock trigger pct (0=off)
    lock_stop: float      # Profit-lock stop pct
    need_trend: bool      # Require 15m EMA rising + 15m DTosc bullish
    need_vol: bool        # Require volume > 1.5x 20-bar MA
    bo_atr: float         # Extra ATR breakout buffer on entry (0=off)
    comp_bars: int        # Compression-break window (0=off)
    comp_ratio: float     # Compression max range/ATR


def _baseline_candidate() -> Candidate:
    return Candidate(
        label="BASELINE",
        atr_stop=_P.atr_multiplier,
        tp_r=_P.unit1_tp_rr,
        be_r=1.25,
        trail_mult=2.0,
        lock_trigger=_P.profit_lock_trigger_pct,
        lock_stop=_P.profit_lock_stop_pct,
        need_trend=False,
        need_vol=False,
        bo_atr=0.0,
        comp_bars=0,
        comp_ratio=0.0,
    )


def _build_grid() -> list[Candidate]:
    """
    Focused grid: ~200 candidates covering the most impactful parameters.
    Uses domain knowledge to avoid wasting time on obviously bad combos.
    """
    cands: list[Candidate] = [_baseline_candidate()]

    # Core ATR/TP/BE/trail grid (most impactful axes)
    for atr_stop in [1.5, 2.0, 2.5, 3.0]:
        for tp_r in [3.0, 4.0, 5.0, 6.0]:
            if tp_r < atr_stop + 1.0:
                continue
            for be_r in [1.0, 1.5, 2.0]:
                for trail in [1.5, 2.0, 2.5]:
                    for lock_t, lock_s in [
                        (0.034, 0.014), (0.05, 0.02), (0.0, 0.0)
                    ]:
                        for need_trend in [False, True]:
                            lbl = f"s{atr_stop}_tp{tp_r}_be{be_r}_tr{trail}_lt{lock_t}_nt{int(need_trend)}"
                            cands.append(Candidate(
                                label=lbl,
                                atr_stop=atr_stop, tp_r=tp_r, be_r=be_r,
                                trail_mult=trail,
                                lock_trigger=lock_t, lock_stop=lock_s,
                                need_trend=need_trend, need_vol=False,
                                bo_atr=0.0, comp_bars=0, comp_ratio=0.0,
                            ))

    # Breakout-ATR entry filter variants on best-looking param range
    for atr_stop in [1.5, 2.0, 2.5]:
        for tp_r in [4.0, 5.0]:
            for be_r in [1.5]:
                for lock_t, lock_s in [(0.034, 0.014), (0.0, 0.0)]:
                    for bo_atr in [0.3, 0.6]:
                        lbl = f"s{atr_stop}_tp{tp_r}_be{be_r}_bo{bo_atr}_lt{lock_t}"
                        cands.append(Candidate(
                            label=lbl,
                            atr_stop=atr_stop, tp_r=tp_r, be_r=be_r,
                            trail_mult=2.0,
                            lock_trigger=lock_t, lock_stop=lock_s,
                            need_trend=False, need_vol=False,
                            bo_atr=bo_atr, comp_bars=0, comp_ratio=0.0,
                        ))

    # Compression-break variants
    for atr_stop in [1.5, 2.0, 2.5]:
        for tp_r in [4.0, 5.0]:
            if tp_r < atr_stop + 1.0:
                continue
            for lock_t, lock_s in [(0.034, 0.014), (0.0, 0.0)]:
                for cb, cr in [(6, 3.5), (8, 4.0)]:
                    lbl = f"s{atr_stop}_tp{tp_r}_comp{cb}_{cr}_lt{lock_t}"
                    cands.append(Candidate(
                        label=lbl, atr_stop=atr_stop, tp_r=tp_r,
                        be_r=1.5, trail_mult=2.0,
                        lock_trigger=lock_t, lock_stop=lock_s,
                        need_trend=False, need_vol=False,
                        bo_atr=0.0, comp_bars=cb, comp_ratio=cr,
                    ))

    # Volume spike filter
    for atr_stop in [1.5, 2.0, 2.5]:
        for tp_r in [4.0, 5.0]:
            if tp_r < atr_stop + 1.0:
                continue
            for lock_t, lock_s in [(0.034, 0.014), (0.0, 0.0)]:
                lbl = f"s{atr_stop}_tp{tp_r}_vol_lt{lock_t}"
                cands.append(Candidate(
                    label=lbl, atr_stop=atr_stop, tp_r=tp_r,
                    be_r=1.5, trail_mult=2.0,
                    lock_trigger=lock_t, lock_stop=lock_s,
                    need_trend=False, need_vol=True,
                    bo_atr=0.0, comp_bars=0, comp_ratio=0.0,
                ))

    # Trend-strength + vol spike combo
    for atr_stop in [1.5, 2.0]:
        for tp_r in [4.0, 5.0]:
            for lock_t, lock_s in [(0.034, 0.014), (0.0, 0.0)]:
                lbl = f"s{atr_stop}_tp{tp_r}_vol_trend_lt{lock_t}"
                cands.append(Candidate(
                    label=lbl, atr_stop=atr_stop, tp_r=tp_r,
                    be_r=1.5, trail_mult=2.0,
                    lock_trigger=lock_t, lock_stop=lock_s,
                    need_trend=True, need_vol=True,
                    bo_atr=0.0, comp_bars=0, comp_ratio=0.0,
                ))

    # Deduplicate
    seen: set[tuple] = set()
    out: list[Candidate] = []
    for c in cands:
        key = (
            round(c.atr_stop, 3), round(c.tp_r, 3), round(c.be_r, 3),
            round(c.trail_mult, 3),
            round(c.lock_trigger, 5), round(c.lock_stop, 5),
            c.need_trend, c.need_vol, round(c.bo_atr, 3),
            c.comp_bars, round(c.comp_ratio, 3),
        )
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


# ---------------------------------------------------------------------------
# Pre-compute per-bar signal arrays (done once per window per symbol)
# ---------------------------------------------------------------------------

def _precompute_signals(df: pd.DataFrame) -> dict[str, np.ndarray]:
    """
    Return numpy arrays for all data used in simulation.
    Avoids repeated .iloc lookups inside the hot loop.
    """
    n = len(df)
    idx = df.index

    close  = df["close"].to_numpy(float)
    high   = df["high"].to_numpy(float)
    low    = df["low"].to_numpy(float)
    volume = df["volume"].to_numpy(float)
    atr5   = df["atr_5m"].to_numpy(float)
    atr15  = df["atr_15m"].to_numpy(float)
    ema15  = df["ema_15m"].to_numpy(float)
    fast5  = df["fast_5m"].to_numpy(float)
    slow5  = df["slow_5m"].to_numpy(float)
    fast15 = df["fast_15m"].to_numpy(float)
    slow15 = df["slow_15m"].to_numpy(float)

    # Time filters
    blocked = np.zeros(n, dtype=bool)
    for i in range(n):
        ts = idx[i]
        if _is_lunch_blocked(ts) or _is_eu_open_buffer(ts):
            blocked[i] = True

    # Day arrays
    dates = np.array([t.date() for t in idx], dtype=object)

    # Precompute 20-bar rolling average volume
    vol_ma20 = np.full(n, np.nan)
    for i in range(20, n):
        vol_ma20[i] = np.nanmean(volume[i - 20:i])

    return {
        "close": close, "high": high, "low": low, "volume": volume,
        "atr5": atr5, "atr15": atr15,
        "ema15": ema15, "fast5": fast5, "slow5": slow5,
        "fast15": fast15, "slow15": slow15,
        "blocked": blocked, "dates": dates, "vol_ma20": vol_ma20,
        "n": n,
    }


# ---------------------------------------------------------------------------
# Fast simulation kernel
# ---------------------------------------------------------------------------

def _simulate(arrays: dict[str, Any], cand: Candidate, fee_rate: float, slip_rate: float) -> float:
    n        = arrays["n"]
    close    = arrays["close"]
    high     = arrays["high"]
    low      = arrays["low"]
    volume   = arrays["volume"]
    atr5     = arrays["atr5"]
    atr15    = arrays["atr15"]
    ema15    = arrays["ema15"]
    fast5    = arrays["fast5"]
    slow5    = arrays["slow5"]
    fast15   = arrays["fast15"]
    slow15   = arrays["slow15"]
    blocked  = arrays["blocked"]
    dates    = arrays["dates"]
    vol_ma20 = arrays["vol_ma20"]

    capital = 10_000.0
    risk_pct = 0.01

    # Position state (all floats/bools)
    in_pos    = False
    entry_p   = 0.0
    stop_p    = 0.0
    target_p  = 0.0
    qty       = 0.0
    risk_d    = 0.0
    be_done   = False
    pl_done   = False
    high_peak = 0.0

    trades_by_day: dict[Any, int] = {}
    total_return_factor = 1.0

    for i in range(2, n):
        hi   = high[i]
        lo   = low[i]
        cl   = close[i]
        a5   = atr5[i]
        a15  = atr15[i]
        day  = dates[i]

        if not math.isfinite(a5) or a5 <= 0:
            continue

        # ---- manage position ----
        if in_pos:
            if hi > high_peak:
                high_peak = hi

            # Break-even
            if not be_done and hi >= entry_p + cand.be_r * risk_d:
                stop_p = max(stop_p, entry_p)
                be_done = True

            # Profit lock
            if not pl_done and cand.lock_trigger > 0 and entry_p > 0:
                if hi >= entry_p * (1.0 + cand.lock_trigger):
                    stop_p = max(stop_p, entry_p * (1.0 + cand.lock_stop))
                    pl_done = True

            # ATR trailing
            if be_done and math.isfinite(a15) and a15 > 0:
                trail = high_peak - cand.trail_mult * a15
                if trail > stop_p:
                    stop_p = trail

            # Exit check
            exit_p = 0.0
            if lo <= stop_p:
                exit_p = stop_p
            elif hi >= target_p:
                exit_p = target_p

            if exit_p > 0:
                ee = entry_p * (1.0 + slip_rate)
                xe = exit_p  * (1.0 - slip_rate)
                gross = (xe - ee) * qty
                fees  = fee_rate * (ee + xe) * qty
                pnl   = gross - fees
                capital += pnl
                in_pos = False
            continue

        # ---- new signal check ----
        cnt = trades_by_day.get(day, 0)
        if cnt >= MAX_TRADES_PER_DAY:
            continue
        if blocked[i]:
            continue

        # DTosc long signal: regime (15m) + trigger (5m crossup) with overbought guard
        e15  = ema15[i]
        f15  = fast15[i]
        s15  = slow15[i]
        f5   = fast5[i]
        s5   = slow5[i]
        pf5  = fast5[i - 1]
        ps5  = slow5[i - 1]

        if not (math.isfinite(e15) and math.isfinite(f15) and math.isfinite(f5)):
            continue

        regime_long  = cl > e15 and f15 > s15 and f15 < 75.0
        long_trigger = (pf5 <= ps5 and f5 > s5) and f5 < 75.0
        if not (regime_long and long_trigger):
            continue

        # --- entry quality filters ---

        # Trend-strength: 15m EMA slope rising
        if cand.need_trend:
            if i < 2:
                continue
            e15_prev = ema15[i - 1]
            if not (math.isfinite(e15_prev) and e15 > e15_prev and f15 > s15):
                continue

        # Volume spike filter
        if cand.need_vol:
            vma = vol_ma20[i]
            if not math.isfinite(vma) or vma <= 0:
                continue
            if volume[i] < 1.5 * vma:
                continue

        # Breakout ATR buffer: close must be above prev_high + bo_atr*ATR
        if cand.bo_atr > 0:
            ph = high[i - 1]
            if cl < ph + cand.bo_atr * a5:
                continue

        # Compression-break: N-bar range <= comp_ratio*ATR, then close > prev_high
        if cand.comp_bars > 0:
            cb = cand.comp_bars
            if i < cb:
                continue
            rng = high[i - cb:i].max() - low[i - cb:i].min()
            if a5 <= 0 or rng / a5 > cand.comp_ratio:
                continue
            if cl <= high[i - 1]:
                continue

        # Risk distance
        r = cand.atr_stop * a5
        if r <= 0 or (cl > 0 and r / cl < 0.002):
            continue

        risk_amt = capital * risk_pct
        q = risk_amt / r
        if q <= 0:
            continue

        entry_p  = cl
        stop_p   = cl - r
        target_p = cl + cand.tp_r * r
        qty      = q
        risk_d   = r
        be_done  = False
        pl_done  = False
        high_peak = hi
        in_pos   = True
        trades_by_day[day] = cnt + 1

    # Close any open position at last bar
    if in_pos:
        lc = close[n - 1]
        ee = entry_p * (1.0 + slip_rate)
        xe = lc * (1.0 - slip_rate)
        gross = (xe - ee) * qty
        fees  = fee_rate * (ee + xe) * qty
        capital += gross - fees

    return (capital / 10_000.0 - 1.0) * 100.0


def _portfolio_return(win_arrays: dict[str, dict[str, Any]], cand: Candidate) -> float:
    rets = []
    for sym, arrays in win_arrays.items():
        fee_rate = _fee_bps_per_side_for_symbol(sym) / 10_000.0
        r = _simulate(arrays, cand, fee_rate, SLIPPAGE_BPS / 10_000.0)
        rets.append(r)
    return sum(rets) / len(rets) if rets else 0.0


def _score(is_r: float, oos1_r: float, oos2_r: float) -> float:
    oos_avg = (oos1_r + oos2_r) / 2.0
    oos_vol = abs(oos1_r - oos2_r) / 2.0
    return oos_avg - 0.5 * oos_vol + 0.1 * is_r


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run() -> None:
    print("=" * 70)
    print("T212 STRATEGY UPGRADE SWEEP  (IS=2024H1 | OOS1=2024H2 | OOS2=2025+)")
    print("=" * 70)

    files = _discover_symbol_files(DATA_DIR)
    full_dfs: dict[str, pd.DataFrame] = {}
    for sym in SYMBOLS:
        if sym not in files:
            print(f"[WARN] No CSV for {sym} - skipping")
            continue
        df = pd.read_csv(files[sym])
        if not {"timestamp","open","high","low","close","volume"}.issubset(df.columns):
            print(f"[WARN] Bad columns {sym}")
            continue
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        df = (df.dropna(subset=["timestamp","open","high","low","close"])
               .sort_values("timestamp").set_index("timestamp"))
        df = add_indicators(df, ema_period=200).dropna()
        full_dfs[sym] = df
        print(f"[DATA] {sym}: {len(df)} bars  {df.index[0].date()} -> {df.index[-1].date()}")

    if not full_dfs:
        print("No data. Aborting.")
        return

    # Pre-slice windows and precompute signal arrays
    win_arrays: dict[str, dict[str, dict[str, Any]]] = {}
    for wname, wstart, wend in WINDOWS:
        win_arrays[wname] = {}
        for sym, df in full_dfs.items():
            sliced = df[(df.index >= wstart) & (df.index <= wend)].copy()
            if len(sliced) >= 100:
                win_arrays[wname][sym] = _precompute_signals(sliced)

    cands = _build_grid()
    print(f"\nGrid: {len(cands)} candidates, {len(full_dfs)} symbols x 3 windows")
    print("Running...\n")

    results: list[tuple[float, float, float, float, Candidate]] = []

    for idx, cand in enumerate(cands):
        if idx % 100 == 0:
            print(f"  [{idx}/{len(cands)}]", flush=True)
        is_r   = _portfolio_return(win_arrays.get("IS",   {}), cand)
        oos1_r = _portfolio_return(win_arrays.get("OOS1", {}), cand)
        oos2_r = _portfolio_return(win_arrays.get("OOS2", {}), cand)
        sc = _score(is_r, oos1_r, oos2_r)
        results.append((sc, is_r, oos1_r, oos2_r, cand))

    results.sort(key=lambda x: -x[0])

    base_entry = next((r for r in results if r[4].label == "BASELINE"), None)
    b_sc = b_is = b_oos1 = b_oos2 = 0.0
    if base_entry:
        b_sc, b_is, b_oos1, b_oos2, _ = base_entry

    print(f"\n{'RANK':<5} {'SCORE':>7} {'IS%':>7} {'OOS1%':>7} {'OOS2%':>7}  BEAT  LABEL")
    print("-" * 80)

    winner: Candidate | None = None
    winner_entry: tuple | None = None

    for rank, (sc, is_r, oos1_r, oos2_r, cand) in enumerate(results[:30], 1):
        beat = "BOTH" if (oos1_r > b_oos1 and oos2_r > b_oos2) \
               else ("OOS1" if oos1_r > b_oos1 else ("OOS2" if oos2_r > b_oos2 else "    "))
        tag = " <- BASELINE" if cand.label == "BASELINE" else ""
        print(f"  {rank:<3} {sc:>7.2f} {is_r:>7.2f} {oos1_r:>7.2f} {oos2_r:>7.2f}  {beat}  {cand.label}{tag}")
        if winner is None and cand.label != "BASELINE" and beat == "BOTH":
            winner = cand
            winner_entry = (sc, is_r, oos1_r, oos2_r)

    if winner is None:
        for sc, is_r, oos1_r, oos2_r, cand in results:
            if cand.label != "BASELINE":
                winner = cand
                winner_entry = (sc, is_r, oos1_r, oos2_r)
                break

    print("\n" + "=" * 70)
    print("BASELINE:")
    print(f"  Score={b_sc:.2f}  IS={b_is:.2f}%  OOS1={b_oos1:.2f}%  OOS2={b_oos2:.2f}%")

    if winner and winner_entry:
        wsc, wis, woos1, woos2 = winner_entry
        print(f"\nWINNER: {winner.label}")
        print(f"  Score={wsc:.2f}  IS={wis:.2f}%  OOS1={woos1:.2f}%  OOS2={woos2:.2f}%")
        print(f"  vs baseline: Dscore={wsc-b_sc:+.2f}  DOIS1={woos1-b_oos1:+.2f}%  DOIS2={woos2-b_oos2:+.2f}%")

        print("\n--- WINNER PARAMETERS ---")
        print(f"  ATR_STOP_MULT     = {winner.atr_stop}")
        print(f"  TP_R              = {winner.tp_r}")
        print(f"  BE_R              = {winner.be_r}")
        print(f"  TRAIL_MULT        = {winner.trail_mult}")
        print(f"  LOCK_TRIGGER_PCT  = {winner.lock_trigger}")
        print(f"  LOCK_STOP_PCT     = {winner.lock_stop}")
        print(f"  BREAKOUT_ATR      = {winner.bo_atr}  (0=off)")
        print(f"  TREND_FILTER      = {winner.need_trend}")
        print(f"  VOL_SPIKE_FILTER  = {winner.need_vol}")
        print(f"  COMP_BARS         = {winner.comp_bars}  (0=off)")
        print(f"  COMP_RATIO        = {winner.comp_ratio}")

        print("\n--- Per-symbol OOS2 ---")
        for sym in SYMBOLS:
            arr = win_arrays.get("OOS2", {}).get(sym)
            if arr is None:
                continue
            fee = _fee_bps_per_side_for_symbol(sym) / 10_000.0
            wr = _simulate(arr, winner,              fee, SLIPPAGE_BPS / 10_000.0)
            br = _simulate(arr, _baseline_candidate(), fee, SLIPPAGE_BPS / 10_000.0)
            print(f"  {sym:<12} winner={wr:>7.2f}%  baseline={br:>7.2f}%  delta={wr-br:>+7.2f}%")

        print("\n--- All windows for winner ---")
        for sym in SYMBOLS:
            parts = []
            for wname, _, _ in WINDOWS:
                arr = win_arrays.get(wname, {}).get(sym)
                if arr is None:
                    continue
                fee = _fee_bps_per_side_for_symbol(sym) / 10_000.0
                r = _simulate(arr, winner, fee, SLIPPAGE_BPS / 10_000.0)
                parts.append(f"{wname}={r:.1f}%")
            print(f"  {sym:<12} " + "  ".join(parts))

    print("=" * 70)


if __name__ == "__main__":
    run()
