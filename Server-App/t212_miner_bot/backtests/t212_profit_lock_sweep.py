"""
Profit-lock sweep for the development strategy.

Tests multiple trigger/lock pairs for the new tiered trailing logic:
- when unrealized profit reaches trigger_pct
- stop is lifted to lock_stop_pct above entry
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import numpy as np
import pandas as pd

from t212_miner_bot.backtests import t212_strategy_compare_4stocks as core
from t212_miner_bot.config import SYMBOLS_MAP, StrategyParams


@dataclass(frozen=True)
class SweepResult:
    trigger_pct: float
    lock_stop_pct: float
    portfolio_return: float
    total_trades: int
    weighted_win_rate: float


def _parse_pct_list(raw: str) -> list[float]:
    out: list[float] = []
    for token in raw.split(","):
        part = token.strip()
        if not part:
            continue
        try:
            value = float(part)
        except ValueError:
            continue
        if value > 0:
            out.append(value)
    return out


def _load_and_prepare(days: int, ema_period: int) -> dict[str, pd.DataFrame]:
    prepared: dict[str, pd.DataFrame] = {}
    for symbol in SYMBOLS_MAP.keys():
        bars = core._load_local_5m_csv(symbol=symbol, days=days)
        if bars.empty:
            bars = core._download_5m_recent(symbol=symbol, days=days)
        if bars.empty:
            prepared[symbol] = pd.DataFrame()
            continue
        prepared[symbol] = core.add_indicators(bars, ema_period=ema_period).dropna().copy()
    return prepared


def _run_one(
    *,
    prepared_by_symbol: dict[str, pd.DataFrame],
    config: core.SimConfig,
    symbol_mode_map: dict[str, str],
    base_cache_by_symbol: dict[str, core.VariantMetrics],
    trigger_pct: float,
    lock_stop_pct: float,
) -> SweepResult:
    returns: list[float] = []
    trade_total = 0
    win_weighted = 0.0

    for symbol, df in prepared_by_symbol.items():
        if df.empty:
            continue
        mode = str(symbol_mode_map.get(symbol, "BASE")).strip().upper()
        atr_metrics = core._simulate_atr_dynamic_variant(
            df,
            symbol=symbol,
            config=config,
            stop_mult=config.atr_stop_multiplier,
            tp_r=config.atr_tp_r,
            be_r=config.atr_be_r,
            entry_filter_mode="NONE",
            entry_filter_param=0.0,
            profit_lock_trigger_pct=trigger_pct,
            profit_lock_stop_pct=lock_stop_pct,
        )
        chosen = base_cache_by_symbol[symbol] if mode == "BASE" else atr_metrics
        returns.append(chosen.total_return)
        trade_total += chosen.total_trades
        win_weighted += (chosen.win_rate / 100.0) * chosen.total_trades

    portfolio_return = float(np.mean(returns)) if returns else 0.0
    weighted_win_rate = (win_weighted / trade_total * 100.0) if trade_total else 0.0
    return SweepResult(
        trigger_pct=trigger_pct,
        lock_stop_pct=lock_stop_pct,
        portfolio_return=portfolio_return,
        total_trades=trade_total,
        weighted_win_rate=weighted_win_rate,
    )


def main() -> None:
    params = StrategyParams()
    parser = argparse.ArgumentParser(description="Sweep profit-lock trigger/stop pairs.")
    parser.add_argument("--days", type=int, default=730, help="Backtest lookback days.")
    parser.add_argument("--fee-bps", type=float, default=0.0, help="Per-side fee in bps.")
    parser.add_argument("--slippage-bps", type=float, default=2.0, help="Per-side slippage in bps.")
    parser.add_argument("--max-trades-per-day", type=int, default=9999, help="Max entries per symbol per day.")
    parser.add_argument(
        "--trigger-values",
        type=str,
        default="0.02,0.025,0.03,0.035",
        help="Comma-separated trigger pct values, e.g. 0.02,0.03",
    )
    parser.add_argument(
        "--lock-values",
        type=str,
        default="0.005,0.008,0.01,0.012",
        help="Comma-separated lock stop pct values, e.g. 0.005,0.01",
    )
    args = parser.parse_args()

    triggers = _parse_pct_list(args.trigger_values)
    locks = _parse_pct_list(args.lock_values)
    if not triggers or not locks:
        raise RuntimeError("No valid trigger/lock values provided.")

    config = core.SimConfig(
        fee_bps=max(args.fee_bps, 0.0),
        slippage_bps=max(args.slippage_bps, 0.0),
        max_trades_per_day=max(args.max_trades_per_day, 1),
        atr_stop_multiplier=max(float(params.atr_dynamic_stop_mult), 0.1),
        atr_tp_r=max(float(params.atr_dynamic_tp_r), 0.1),
        atr_be_r=max(float(params.atr_dynamic_be_r), 0.1),
    )
    symbol_mode_map = dict(params.symbol_strategy_mode)

    print(
        f"[INFO] Profit-lock sweep | days={args.days} fee_bps={config.fee_bps:.2f} "
        f"slippage_bps={config.slippage_bps:.2f} max_trades={config.max_trades_per_day}"
    )
    print(f"[INFO] Hybrid modes: {symbol_mode_map}")
    prepared_by_symbol = _load_and_prepare(days=args.days, ema_period=params.ema_period)
    for symbol, df in prepared_by_symbol.items():
        print(f"[INFO] {symbol}: prepared_rows={len(df)}")

    # Optimization: simulations already receive prepared frames.
    core.add_indicators = lambda df_raw, ema_period: df_raw

    base_cache_by_symbol: dict[str, core.VariantMetrics] = {}
    for symbol, df in prepared_by_symbol.items():
        if df.empty:
            continue
        base_cache_by_symbol[symbol] = core._simulate_symbol_variant(
            df,
            symbol=symbol,
            enable_break_even_1pct=False,
            config=config,
            entry_filter_mode="NONE",
            entry_filter_param=0.0,
            profit_lock_trigger_pct=0.0,
            profit_lock_stop_pct=0.0,
        )

    baseline = _run_one(
        prepared_by_symbol=prepared_by_symbol,
        config=config,
        symbol_mode_map=symbol_mode_map,
        base_cache_by_symbol=base_cache_by_symbol,
        trigger_pct=0.0,
        lock_stop_pct=0.0,
    )
    print(
        f"[RUN] BASELINE: ret={baseline.portfolio_return:.2f}% "
        f"trades={baseline.total_trades} win={baseline.weighted_win_rate:.2f}%"
    )

    results: list[SweepResult] = []
    for trigger in triggers:
        for lock in locks:
            if lock >= trigger:
                continue
            row = _run_one(
                prepared_by_symbol=prepared_by_symbol,
                config=config,
                symbol_mode_map=symbol_mode_map,
                base_cache_by_symbol=base_cache_by_symbol,
                trigger_pct=trigger,
                lock_stop_pct=lock,
            )
            results.append(row)
            print(
                f"[RUN] trigger={trigger:.4f} lock={lock:.4f} "
                f"ret={row.portfolio_return:.2f}% trades={row.total_trades} win={row.weighted_win_rate:.2f}%"
            )

    ranked = sorted(results, key=lambda x: x.portfolio_return, reverse=True)
    print("\n" + "=" * 104)
    print("PROFIT-LOCK SWEEP RANKING")
    print("=" * 104)
    print(f"{'Rank':<6} {'Trigger%':>10} {'Lock%':>10} {'Return%':>11} {'Delta vs Base%':>15} {'Trades':>10} {'Win%':>10}")
    print("-" * 104)
    for i, row in enumerate(ranked, start=1):
        delta = row.portfolio_return - baseline.portfolio_return
        print(
            f"{i:<6} {row.trigger_pct * 100:>9.2f} {row.lock_stop_pct * 100:>9.2f} "
            f"{row.portfolio_return:>11.2f} {delta:>15.2f} {row.total_trades:>10d} {row.weighted_win_rate:>10.2f}"
        )
    print("-" * 104)
    if ranked:
        best = ranked[0]
        print(
            f"[RESULT] Best trigger={best.trigger_pct:.4f} lock={best.lock_stop_pct:.4f} "
            f"ret={best.portfolio_return:.2f}% | baseline={baseline.portfolio_return:.2f}% "
            f"| delta={best.portfolio_return - baseline.portfolio_return:.2f}%"
        )
    print("=" * 104)


if __name__ == "__main__":
    main()
