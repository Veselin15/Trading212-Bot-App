"""
Expectancy report (per symbol) for the *current live bot logic* using historical CSV data.

Why this exists
---------------
Your Trading212 exports only contain trades since you started the bot (e.g. 2026-04-02),
so per-symbol performance there is too short to judge. This script simulates older history
with the exact same long-only strategy logic (Engine A style) and reports:

- total return %
- trade count
- win rate
- avg win / avg loss
- profit factor
- expectancy per trade

Run (repo root):
  python -m t212_miner_bot.backtests.t212_expectancy_report
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

START = pd.Timestamp("2024-01-01", tz="UTC")
END = pd.Timestamp("2026-04-01", tz="UTC")

EMA_PERIOD = 200
MAX_TRADES_PER_DAY = 2
SLIPPAGE_BPS = 10.0


@dataclass(frozen=True)
class Candidate:
    atr_stop: float
    tp_rr: float
    be_r: float
    be_pct: float
    trail_mult: float
    lock_trigger: float
    lock_stop: float
    entry_filter: str  # NONE or TREND (live currently NONE per latest config)
    entry_param: float


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

    # Time filter (same rough UTC windows used elsewhere in repo):
    blocked = np.zeros(n, dtype=bool)
    for i, ts in enumerate(df.index):
        # lunch block (UTC) and EU open buffer (UTC)
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


def _entry_ok(arr: SymArrays, i: int, cand: Candidate) -> bool:
    if cand.entry_filter in ("", "NONE"):
        return True
    if cand.entry_filter == "TREND":
        if i < 2:
            return False
        e15 = arr.ema15[i]
        e15p = arr.ema15[i - 1]
        f15 = arr.fast15[i]
        s15 = arr.slow15[i]
        return math.isfinite(e15) and math.isfinite(e15p) and (e15 > e15p) and (f15 > s15)
    return True


def _cost_adjust_trade_ret(trade_ret: float, fee_r: float, slip_r: float, qty_frac: float) -> float:
    # This mirrors the simplified approach used in the fast lab: fees as a fraction + slip on both sides.
    return trade_ret * (1.0 - fee_r) - slip_r * 2.0 * qty_frac


def _sim_base_trades(arr: SymArrays, cand: Candidate, fee_r: float, slip_r: float) -> tuple[float, list[float]]:
    """
    BASE mode returns:
      - total return % (equity multiplier)
      - trade list of per-trade returns (as fractions, e.g. 0.01 == +1%)
    """
    n = arr.n
    equity = 1.0
    trades: list[float] = []
    day_trade_cnt: dict[int, int] = {}

    in_pos = False
    pending = False
    pend_stop = 0.0
    pend_risk = 0.0

    entry_p = stop_p = unit1_tp = 0.0
    qty_open = 0.0
    unit1_done = False
    high_pk = 0.0
    realized = 0.0
    be_moved = False

    for i in range(2, n):
        hi = arr.high[i]
        lo = arr.low[i]
        cl = arr.close[i]
        a15 = arr.atr15[i]
        day = int(arr.day_idx[i])

        if in_pos:
            if not be_moved and hi >= entry_p * (1.0 + cand.be_pct):
                stop_p = max(stop_p, entry_p)
                be_moved = True

            if cand.lock_trigger > 0 and hi >= entry_p * (1.0 + cand.lock_trigger):
                stop_p = max(stop_p, entry_p * (1.0 + cand.lock_stop))

            if lo <= stop_p:
                leg = qty_open * ((stop_p - entry_p) / entry_p)
                leg_net = _cost_adjust_trade_ret(leg, fee_r, slip_r, qty_open)
                pnl = realized + leg_net
                equity *= 1.0 + pnl
                trades.append(pnl)
                in_pos = False
                continue

            if not unit1_done and cl >= unit1_tp:
                half = 0.5
                raw = half * ((cl - entry_p) / entry_p)
                realized += _cost_adjust_trade_ret(raw, fee_r, slip_r, half)
                qty_open -= half
                unit1_done = True
                stop_p = max(stop_p, entry_p * (1.0 + 0.0015))

            if unit1_done and qty_open > 0:
                high_pk = max(high_pk, hi)
                if math.isfinite(a15) and a15 > 0:
                    stop_p = max(stop_p, high_pk - cand.trail_mult * a15)
                if lo <= stop_p:
                    leg = qty_open * ((stop_p - entry_p) / entry_p)
                    leg_net = _cost_adjust_trade_ret(leg, fee_r, slip_r, qty_open)
                    pnl = realized + leg_net
                    equity *= 1.0 + pnl
                    trades.append(pnl)
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

        if not arr.long_sig[i]:
            continue
        if arr.blocked[i]:
            continue
        if not _entry_ok(arr, i, cand):
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
        leg_net = _cost_adjust_trade_ret(leg, fee_r, slip_r, qty_open)
        pnl = realized + leg_net
        equity *= 1.0 + pnl
        trades.append(pnl)

    return (equity - 1.0) * 100.0, trades


def _sim_atr_trades(arr: SymArrays, cand: Candidate, fee_r: float, slip_r: float) -> tuple[float, list[float]]:
    """
    ATR mode returns:
      - total return % (on 10k capital)
      - trade list as *percent of initial capital* per trade
    """
    n = arr.n
    capital = 10_000.0
    risk_pct = 0.02
    trades_pct: list[float] = []
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
                trades_pct.append((pnl_eur / 10_000.0))
                in_pos = False
            continue

        if not arr.long_sig[i]:
            continue
        if arr.blocked[i]:
            continue
        if not _entry_ok(arr, i, cand):
            continue
        if day_trade_cnt.get(day, 0) >= MAX_TRADES_PER_DAY:
            continue

        a5 = arr.atr5[i]
        if not (math.isfinite(a5) and a5 > 0):
            continue
        risk_d = cand.atr_stop * a5
        if risk_d <= 0:
            continue
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
        trades_pct.append((pnl_eur / 10_000.0))

    return (capital / 10_000.0 - 1.0) * 100.0, trades_pct


def _stats(trades: list[float]) -> dict[str, float]:
    if not trades:
        return {"n": 0, "win_rate": 0.0, "avg_win": 0.0, "avg_loss": 0.0, "pf": 0.0, "exp": 0.0}
    wins = [t for t in trades if t > 0]
    losses = [-t for t in trades if t < 0]
    n = len(trades)
    win_rate = (len(wins) / n) * 100.0
    avg_win = (sum(wins) / len(wins)) if wins else 0.0
    avg_loss = (sum(losses) / len(losses)) if losses else 0.0
    pf = (sum(wins) / sum(losses)) if losses else float("inf")
    exp = sum(trades) / n
    return {"n": n, "win_rate": win_rate, "avg_win": avg_win, "avg_loss": avg_loss, "pf": pf, "exp": exp}


def main() -> None:
    params = StrategyParams()
    cand = Candidate(
        atr_stop=float(params.atr_multiplier),
        tp_rr=float(params.unit1_tp_rr),
        be_r=float(params.atr_dynamic_be_r),
        be_pct=float(params.break_even_trigger_pct),
        trail_mult=float(params.atr_trail_mult),
        lock_trigger=float(params.profit_lock_trigger_pct),
        lock_stop=float(params.profit_lock_stop_pct),
        entry_filter=("TREND" if bool(params.trend_strength_filter_enabled) else "NONE"),
        entry_param=0.0,
    )

    files = _discover_symbol_files(DATA_DIR)
    print(f"Range: {START.date()} -> {END.date()} | slippage={SLIPPAGE_BPS}bps")
    print(f"Live params: atr_stop={cand.atr_stop} tp_rr={cand.tp_rr} be_r={cand.be_r} trail={cand.trail_mult} lock={cand.lock_trigger}/{cand.lock_stop} entry_filter={cand.entry_filter}")
    print()
    print(f"{'Symbol':<10} {'Mode':<4} {'Ret%':>9} {'Trades':>7} {'Win%':>7} {'AvgWin%':>9} {'AvgLoss%':>10} {'PF':>7} {'Exp%/tr':>9}")
    print("-" * 90)

    port_rets = []
    for sym in SYMBOLS:
        f = files.get(sym)
        if not f:
            print(f"{sym:<10} {'-':<4} {'N/A':>9} {'-':>7} {'-':>7} {'-':>9} {'-':>10} {'-':>7} {'-':>9}")
            continue
        df = pd.read_csv(f)
        if "timestamp" not in df.columns:
            # fall back: first time-like column
            ts_col = next((c for c in df.columns if "time" in c.lower() or "date" in c.lower()), None)
        else:
            ts_col = "timestamp"
        df[ts_col] = pd.to_datetime(df[ts_col], utc=True, errors="coerce")
        df = df.dropna(subset=[ts_col]).sort_values(ts_col).set_index(ts_col)
        df.columns = [c.lower() for c in df.columns]
        df = df[["open", "high", "low", "close", "volume"]].dropna()
        df = df[(df.index >= START) & (df.index <= END)]
        if len(df) < 200:
            print(f"{sym:<10} {'-':<4} {'N/A':>9} {'-':>7} {'-':>7} {'-':>9} {'-':>10} {'-':>7} {'-':>9}")
            continue

        dfp = add_indicators(df, ema_period=EMA_PERIOD).dropna()
        arr = _precompute(dfp)
        fee_r = _fee_bps_per_side_for_symbol(sym) / 10_000.0
        slip_r = SLIPPAGE_BPS / 10_000.0

        mode = SYMBOL_MODE_MAP.get(sym, "BASE")
        if mode == "ATR":
            ret, trades = _sim_atr_trades(arr, cand, fee_r, slip_r)
        else:
            ret, trades = _sim_base_trades(arr, cand, fee_r, slip_r)

        s = _stats(trades)
        port_rets.append(ret)
        # trades are fractions; display % for avg win/loss/exp
        pf = s["pf"]
        pf_txt = f"{pf:.2f}" if math.isfinite(pf) else "inf"
        print(
            f"{sym:<10} {mode:<4} {ret:>+9.2f} "
            f"{int(s['n']):>7d} {s['win_rate']:>6.1f}% "
            f"{(s['avg_win']*100):>+8.2f}% {(s['avg_loss']*100):>+9.2f}% "
            f"{pf_txt:>7} {(s['exp']*100):>+8.2f}%"
        )

    if port_rets:
        print("-" * 90)
        print(f"{'PORTFOLIO':<10} {'AVG':<4} {sum(port_rets)/len(port_rets):>+9.2f}")


if __name__ == "__main__":
    main()

