"""
Per-symbol parameter optimizer for the cost-aware best-5 basket.

Goal:
- Start from the current live strategy logic.
- Find best 5 symbols under Bulgaria/Trading212 costs.
- Tune custom parameters per symbol (mode + profit lock + morning protect + ATR risk).
- Report portfolio improvement vs untuned best-5 baseline.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from itertools import product
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from t212_miner_bot.backtests import t212_strategy_compare_4stocks as core
from t212_miner_bot.backtests.t212_bulgaria_fee_tax_portfolio_test import (
    _discover_symbol_files,
    _fee_bps_per_side_for_symbol,
    _load_csv,
)
from t212_miner_bot.config import StrategyParams


DATA_DIR = REPO_ROOT / "data"


@dataclass(frozen=True)
class TunedSymbol:
    symbol: str
    mode: str
    fee_bps_per_side: float
    total_return: float
    win_rate: float
    trades: int
    profit_factor: float
    profit_lock_trigger_pct: float
    profit_lock_stop_pct: float
    morning_enabled: bool
    morning_real_profit_trigger_pct: float
    morning_profit_capture_pct: float
    morning_window_minutes: int
    atr_stop_mult: float
    atr_tp_r: float
    atr_be_r: float


def _fmt_pf(value: float) -> str:
    return f"{value:.2f}" if math.isfinite(value) else "inf"


def _portfolio_avg_return(rows: list[TunedSymbol]) -> float:
    if not rows:
        return 0.0
    return float(sum(r.total_return for r in rows) / len(rows))


def _simulate_one(
    *,
    symbol: str,
    bars: pd.DataFrame,
    mode: str,
    fee_bps: float,
    slippage_bps: float,
    max_trades_per_day: int,
    params: StrategyParams,
    profit_lock_trigger_pct: float,
    profit_lock_stop_pct: float,
    morning_enabled: bool,
    morning_real_profit_trigger_pct: float,
    morning_profit_capture_pct: float,
    morning_window_minutes: int,
    atr_stop_mult: float,
    atr_tp_r: float,
    atr_be_r: float,
) -> core.VariantMetrics:
    config = core.SimConfig(
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        max_trades_per_day=max_trades_per_day,
        atr_stop_multiplier=atr_stop_mult,
        atr_tp_r=atr_tp_r,
        atr_be_r=atr_be_r,
        morning_protect_enabled=morning_enabled,
        morning_real_profit_trigger_pct=morning_real_profit_trigger_pct,
        morning_profit_capture_pct=morning_profit_capture_pct,
        morning_protect_window_minutes=morning_window_minutes,
        morning_protect_symbol_enabled={symbol: morning_enabled},
    )
    mode_u = str(mode).strip().upper()
    if mode_u == "ATR":
        return core._simulate_atr_dynamic_variant(
            bars,
            symbol=symbol,
            config=config,
            stop_mult=atr_stop_mult,
            tp_r=atr_tp_r,
            be_r=atr_be_r,
            entry_filter_mode="NONE",
            entry_filter_param=0.0,
            regime_adaptive=False,
            profit_lock_trigger_pct=profit_lock_trigger_pct,
            profit_lock_stop_pct=profit_lock_stop_pct,
        )
    return core._simulate_symbol_variant(
        bars,
        symbol=symbol,
        enable_break_even_1pct=False,
        config=config,
        entry_filter_mode="NONE",
        entry_filter_param=0.0,
        profit_lock_trigger_pct=profit_lock_trigger_pct,
        profit_lock_stop_pct=profit_lock_stop_pct,
    )


def _select_best5_baseline(
    *,
    bars_by_symbol: dict[str, pd.DataFrame],
    params: StrategyParams,
    slippage_bps: float,
    max_trades_per_day: int,
    min_trades: int,
) -> list[TunedSymbol]:
    out: list[TunedSymbol] = []
    total = len(bars_by_symbol)
    for idx, (symbol, bars) in enumerate(bars_by_symbol.items(), start=1):
        if bars.empty:
            continue
        print(f"[BASELINE] {idx}/{total} {symbol}: simulating BASE/ATR...", flush=True)
        fee_bps = _fee_bps_per_side_for_symbol(symbol)
        morning_flag = bool(params.morning_protect_symbol_enabled.get(symbol, False))
        base = _simulate_one(
            symbol=symbol,
            bars=bars,
            mode="BASE",
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
            max_trades_per_day=max_trades_per_day,
            params=params,
            profit_lock_trigger_pct=float(params.profit_lock_trigger_pct),
            profit_lock_stop_pct=float(params.profit_lock_stop_pct),
            morning_enabled=morning_flag and bool(params.morning_protect_enabled),
            morning_real_profit_trigger_pct=float(params.morning_real_profit_trigger_pct),
            morning_profit_capture_pct=float(params.morning_profit_capture_pct),
            morning_window_minutes=int(params.morning_protect_window_minutes),
            atr_stop_mult=float(params.atr_dynamic_stop_mult),
            atr_tp_r=float(params.atr_dynamic_tp_r),
            atr_be_r=float(params.atr_dynamic_be_r),
        )
        atr = _simulate_one(
            symbol=symbol,
            bars=bars,
            mode="ATR",
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
            max_trades_per_day=max_trades_per_day,
            params=params,
            profit_lock_trigger_pct=float(params.profit_lock_trigger_pct),
            profit_lock_stop_pct=float(params.profit_lock_stop_pct),
            morning_enabled=morning_flag and bool(params.morning_protect_enabled),
            morning_real_profit_trigger_pct=float(params.morning_real_profit_trigger_pct),
            morning_profit_capture_pct=float(params.morning_profit_capture_pct),
            morning_window_minutes=int(params.morning_protect_window_minutes),
            atr_stop_mult=float(params.atr_dynamic_stop_mult),
            atr_tp_r=float(params.atr_dynamic_tp_r),
            atr_be_r=float(params.atr_dynamic_be_r),
        )
        chosen = atr if atr.total_return > base.total_return else base
        if chosen.total_trades < min_trades:
            continue
        out.append(
            TunedSymbol(
                symbol=symbol,
                mode="ATR" if chosen is atr else "BASE",
                fee_bps_per_side=fee_bps,
                total_return=chosen.total_return,
                win_rate=chosen.win_rate,
                trades=chosen.total_trades,
                profit_factor=chosen.profit_factor,
                profit_lock_trigger_pct=float(params.profit_lock_trigger_pct),
                profit_lock_stop_pct=float(params.profit_lock_stop_pct),
                morning_enabled=morning_flag and bool(params.morning_protect_enabled),
                morning_real_profit_trigger_pct=float(params.morning_real_profit_trigger_pct),
                morning_profit_capture_pct=float(params.morning_profit_capture_pct),
                morning_window_minutes=int(params.morning_protect_window_minutes),
                atr_stop_mult=float(params.atr_dynamic_stop_mult),
                atr_tp_r=float(params.atr_dynamic_tp_r),
                atr_be_r=float(params.atr_dynamic_be_r),
            )
        )
    ranked = sorted(out, key=lambda r: r.total_return, reverse=True)
    return ranked[:5]


def _optimize_symbol(
    *,
    base_row: TunedSymbol,
    bars: pd.DataFrame,
    params: StrategyParams,
    slippage_bps: float,
    max_trades_per_day: int,
    quick: bool,
) -> TunedSymbol:
    fee_bps = base_row.fee_bps_per_side
    profit_triggers = [0.025, 0.03, 0.034, 0.04]
    profit_locks = [0.008, 0.012, 0.014, 0.018]
    if quick:
        profit_triggers = [0.03, 0.034]
        profit_locks = [0.012, 0.014]

    morning_real_profit = [0.005, 0.01, 0.015]
    morning_capture = [0.15, 0.25, 0.35]
    morning_windows = [60, 120]
    morning_enabled_values = [False, True]
    if quick:
        morning_real_profit = [0.01]
        morning_capture = [0.25]
        morning_windows = [120]
        morning_enabled_values = [False, True]

    atr_stop_values = [2.0, 2.5, 3.0]
    atr_tp_values = [3.0, 4.0, 5.0]
    atr_be_values = [1.2, 1.8, 2.2]
    if quick:
        atr_stop_values = [2.5]
        atr_tp_values = [4.0]
        atr_be_values = [1.8, 2.2]

    best = base_row

    # Stage 1: mode + profit-lock (keep other params from baseline row).
    for mode in ("BASE", "ATR"):
        for trigger, lock in product(profit_triggers, profit_locks):
            if lock >= trigger:
                continue
            metrics = _simulate_one(
                symbol=base_row.symbol,
                bars=bars,
                mode=mode,
                fee_bps=fee_bps,
                slippage_bps=slippage_bps,
                max_trades_per_day=max_trades_per_day,
                params=params,
                profit_lock_trigger_pct=trigger,
                profit_lock_stop_pct=lock,
                morning_enabled=best.morning_enabled,
                morning_real_profit_trigger_pct=best.morning_real_profit_trigger_pct,
                morning_profit_capture_pct=best.morning_profit_capture_pct,
                morning_window_minutes=best.morning_window_minutes,
                atr_stop_mult=best.atr_stop_mult,
                atr_tp_r=best.atr_tp_r,
                atr_be_r=best.atr_be_r,
            )
            if metrics.total_return > best.total_return:
                best = TunedSymbol(
                    symbol=base_row.symbol,
                    mode=mode,
                    fee_bps_per_side=fee_bps,
                    total_return=metrics.total_return,
                    win_rate=metrics.win_rate,
                    trades=metrics.total_trades,
                    profit_factor=metrics.profit_factor,
                    profit_lock_trigger_pct=trigger,
                    profit_lock_stop_pct=lock,
                    morning_enabled=best.morning_enabled,
                    morning_real_profit_trigger_pct=best.morning_real_profit_trigger_pct,
                    morning_profit_capture_pct=best.morning_profit_capture_pct,
                    morning_window_minutes=best.morning_window_minutes,
                    atr_stop_mult=best.atr_stop_mult,
                    atr_tp_r=best.atr_tp_r,
                    atr_be_r=best.atr_be_r,
                )

    # Stage 2: morning settings.
    for enabled, real_trigger, capture, window in product(
        morning_enabled_values, morning_real_profit, morning_capture, morning_windows
    ):
        metrics = _simulate_one(
            symbol=base_row.symbol,
            bars=bars,
            mode=best.mode,
            fee_bps=fee_bps,
            slippage_bps=slippage_bps,
            max_trades_per_day=max_trades_per_day,
            params=params,
            profit_lock_trigger_pct=best.profit_lock_trigger_pct,
            profit_lock_stop_pct=best.profit_lock_stop_pct,
            morning_enabled=enabled,
            morning_real_profit_trigger_pct=real_trigger,
            morning_profit_capture_pct=capture,
            morning_window_minutes=window,
            atr_stop_mult=best.atr_stop_mult,
            atr_tp_r=best.atr_tp_r,
            atr_be_r=best.atr_be_r,
        )
        if metrics.total_return > best.total_return:
            best = TunedSymbol(
                symbol=base_row.symbol,
                mode=best.mode,
                fee_bps_per_side=fee_bps,
                total_return=metrics.total_return,
                win_rate=metrics.win_rate,
                trades=metrics.total_trades,
                profit_factor=metrics.profit_factor,
                profit_lock_trigger_pct=best.profit_lock_trigger_pct,
                profit_lock_stop_pct=best.profit_lock_stop_pct,
                morning_enabled=enabled,
                morning_real_profit_trigger_pct=real_trigger,
                morning_profit_capture_pct=capture,
                morning_window_minutes=window,
                atr_stop_mult=best.atr_stop_mult,
                atr_tp_r=best.atr_tp_r,
                atr_be_r=best.atr_be_r,
            )

    # Stage 3: ATR risk tuning (only useful when mode=ATR).
    if best.mode == "ATR":
        for stop_mult, tp_r, be_r in product(atr_stop_values, atr_tp_values, atr_be_values):
            metrics = _simulate_one(
                symbol=base_row.symbol,
                bars=bars,
                mode=best.mode,
                fee_bps=fee_bps,
                slippage_bps=slippage_bps,
                max_trades_per_day=max_trades_per_day,
                params=params,
                profit_lock_trigger_pct=best.profit_lock_trigger_pct,
                profit_lock_stop_pct=best.profit_lock_stop_pct,
                morning_enabled=best.morning_enabled,
                morning_real_profit_trigger_pct=best.morning_real_profit_trigger_pct,
                morning_profit_capture_pct=best.morning_profit_capture_pct,
                morning_window_minutes=best.morning_window_minutes,
                atr_stop_mult=stop_mult,
                atr_tp_r=tp_r,
                atr_be_r=be_r,
            )
            if metrics.total_return > best.total_return:
                best = TunedSymbol(
                    symbol=base_row.symbol,
                    mode="ATR",
                    fee_bps_per_side=fee_bps,
                    total_return=metrics.total_return,
                    win_rate=metrics.win_rate,
                    trades=metrics.total_trades,
                    profit_factor=metrics.profit_factor,
                    profit_lock_trigger_pct=best.profit_lock_trigger_pct,
                    profit_lock_stop_pct=best.profit_lock_stop_pct,
                    morning_enabled=best.morning_enabled,
                    morning_real_profit_trigger_pct=best.morning_real_profit_trigger_pct,
                    morning_profit_capture_pct=best.morning_profit_capture_pct,
                    morning_window_minutes=best.morning_window_minutes,
                    atr_stop_mult=stop_mult,
                    atr_tp_r=tp_r,
                    atr_be_r=be_r,
                )
    return best


def _print_rows(title: str, rows: list[TunedSymbol]) -> None:
    print("\n" + "=" * 160)
    print(title)
    print("=" * 160)
    print(
        f"{'Symbol':<11} {'Mode':>5} {'Ret%':>9} {'Win%':>8} {'Trades':>8} {'PF':>7} "
        f"{'PL Trigger%':>12} {'PL Stop%':>10} {'Morning':>8} {'M Real%':>8} {'M Cap%':>8} {'M Win':>6} "
        f"{'ATR Stop':>9} {'ATR TP':>8} {'ATR BE':>8}"
    )
    print("-" * 160)
    for r in rows:
        print(
            f"{r.symbol:<11} {r.mode:>5} {r.total_return:>9.2f} {r.win_rate:>8.2f} {r.trades:>8d} {_fmt_pf(r.profit_factor):>7} "
            f"{r.profit_lock_trigger_pct * 100:>12.2f} {r.profit_lock_stop_pct * 100:>10.2f} "
            f"{str(r.morning_enabled):>8} {r.morning_real_profit_trigger_pct * 100:>8.2f} {r.morning_profit_capture_pct * 100:>8.2f} {r.morning_window_minutes:>6d} "
            f"{r.atr_stop_mult:>9.2f} {r.atr_tp_r:>8.2f} {r.atr_be_r:>8.2f}"
        )
    print("-" * 160)
    print(f"PORTFOLIO AVG RETURN: {_portfolio_avg_return(rows):.2f}%")
    print("=" * 160)


def run(days: int, min_trades: int, slippage_bps: float, max_trades_per_day: int, quick: bool) -> None:
    params = StrategyParams()
    symbol_files = _discover_symbol_files(DATA_DIR)
    if not symbol_files:
        raise RuntimeError(f"No *_5m.csv files found in {DATA_DIR}")

    bars_by_symbol: dict[str, pd.DataFrame] = {}
    for symbol, path in sorted(symbol_files.items()):
        bars_raw = _load_csv(path, days=days)
        if bars_raw.empty:
            continue
        prepared = core.add_indicators(bars_raw, ema_period=params.ema_period).dropna().copy()
        if prepared.empty:
            continue
        bars_by_symbol[symbol] = prepared
    print(
        f"[INFO] Best5 optimizer | days={days} symbols={len(bars_by_symbol)} min_trades={min_trades} "
        f"slippage_bps={slippage_bps:.2f} quick={quick}",
        flush=True,
    )
    # Performance optimization: simulations below receive already-prepared indicator frames.
    core.add_indicators = lambda df_raw, ema_period: df_raw
    print("[INFO] Selecting baseline best-5 first...", flush=True)

    baseline_best5 = _select_best5_baseline(
        bars_by_symbol=bars_by_symbol,
        params=params,
        slippage_bps=slippage_bps,
        max_trades_per_day=max_trades_per_day,
        min_trades=min_trades,
    )
    if len(baseline_best5) < 5:
        raise RuntimeError(
            f"Only {len(baseline_best5)} symbols passed min-trades filter ({min_trades}). "
            "Lower --min-trades if needed."
        )

    _print_rows("BASELINE BEST-5 (COST-AWARE, LIVE PARAMS)", baseline_best5)
    print("[INFO] Optimizing each symbol independently...", flush=True)

    tuned_rows: list[TunedSymbol] = []
    for row in baseline_best5:
        bars = bars_by_symbol[row.symbol]
        print(f"[OPT] {row.symbol}: tuning custom parameters...", flush=True)
        tuned = _optimize_symbol(
            base_row=row,
            bars=bars,
            params=params,
            slippage_bps=slippage_bps,
            max_trades_per_day=max_trades_per_day,
            quick=quick,
        )
        tuned_rows.append(tuned)
        print(
            f"[TUNED] {row.symbol:<11} {row.total_return:>8.2f}% -> {tuned.total_return:>8.2f}% "
            f"(delta {tuned.total_return - row.total_return:>6.2f} pp)"
        , flush=True)

    tuned_rows = sorted(tuned_rows, key=lambda x: x.total_return, reverse=True)
    _print_rows("TUNED BEST-5 (PER-SYMBOL CUSTOM PARAMS)", tuned_rows)

    base_avg = _portfolio_avg_return(baseline_best5)
    tuned_avg = _portfolio_avg_return(tuned_rows)
    print("\n" + "=" * 90)
    print("SUMMARY")
    print("=" * 90)
    print(f"Baseline best-5 avg return: {base_avg:.2f}%")
    print(f"Tuned best-5 avg return:    {tuned_avg:.2f}%")
    print(f"Delta:                     {tuned_avg - base_avg:.2f} pp")
    print("=" * 90)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Optimize custom per-symbol params for the cost-aware best-5 basket."
    )
    parser.add_argument("--days", type=int, default=730, help="Backtest lookback days (default: 730).")
    parser.add_argument("--min-trades", type=int, default=80, help="Minimum trades per symbol (default: 80).")
    parser.add_argument(
        "--slippage-bps",
        type=float,
        default=5.0,
        help="Per-side slippage bps (default: 5.0).",
    )
    parser.add_argument(
        "--max-trades-per-day",
        type=int,
        default=9999,
        help="Max new entries per symbol/day (default: 9999).",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Reduced search grid for faster iteration.",
    )
    args = parser.parse_args()
    run(
        days=max(args.days, 30),
        min_trades=max(args.min_trades, 0),
        slippage_bps=max(args.slippage_bps, 0.0),
        max_trades_per_day=max(args.max_trades_per_day, 1),
        quick=bool(args.quick),
    )


if __name__ == "__main__":
    main()
