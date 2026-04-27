"""
Strategy upgrade lab sweep.

Runs a broad parameter grid for regime-adaptive ATR risk and compares each
candidate against the current live hybrid baseline on the same 4-symbol universe.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import numpy as np
import pandas as pd

from t212_miner_bot.backtests import t212_strategy_compare_4stocks as core
from t212_miner_bot.config import SYMBOLS_MAP, StrategyParams


@dataclass(frozen=True)
class Candidate:
    name: str
    entry_filter_mode: str
    entry_filter_param: float
    atr_map: dict[str, tuple[float, float, float]]
    regime_adaptive: bool
    regime_profiles: dict[str, tuple[float, float, float]]


@dataclass(frozen=True)
class PortfolioResult:
    name: str
    portfolio_return: float
    total_trades: int
    weighted_win_rate: float


def _load_bars(days: int) -> dict[str, pd.DataFrame]:
    bars_by_symbol: dict[str, pd.DataFrame] = {}
    for symbol in SYMBOLS_MAP.keys():
        bars = core._load_local_5m_csv(symbol=symbol, days=days)
        if bars.empty:
            bars = core._download_5m_recent(symbol=symbol, days=days)
        bars_by_symbol[symbol] = bars
    return bars_by_symbol


def _prepare_indicator_frames(
    bars_by_symbol: dict[str, pd.DataFrame],
    ema_period: int,
) -> dict[str, pd.DataFrame]:
    prepared: dict[str, pd.DataFrame] = {}
    for symbol, bars in bars_by_symbol.items():
        if bars.empty:
            prepared[symbol] = pd.DataFrame()
            continue
        prepared[symbol] = core.add_indicators(bars, ema_period=ema_period).dropna().copy()
    return prepared


def _simulate_portfolio(
    *,
    prepared_by_symbol: dict[str, pd.DataFrame],
    config: core.SimConfig,
    symbol_mode_map: dict[str, str],
    entry_filter_mode: str,
    entry_filter_param: float,
    atr_map: dict[str, tuple[float, float, float]],
    regime_adaptive: bool,
    regime_profiles: dict[str, tuple[float, float, float]],
    base_cache_by_symbol: dict[str, core.VariantMetrics],
    label: str,
) -> PortfolioResult:
    symbol_returns: list[float] = []
    total_trades = 0
    weighted_wins = 0.0

    for symbol, df in prepared_by_symbol.items():
        if df.empty:
            continue
        mode = str(symbol_mode_map.get(symbol, "BASE")).strip().upper()
        stop_mult, tp_r, be_r = atr_map.get(
            symbol,
            (config.atr_stop_multiplier, config.atr_tp_r, config.atr_be_r),
        )
        atr_metrics = core._simulate_atr_dynamic_variant(
            df,
            symbol=symbol,
            config=config,
            stop_mult=stop_mult,
            tp_r=tp_r,
            be_r=be_r,
            entry_filter_mode=entry_filter_mode,
            entry_filter_param=entry_filter_param,
            regime_adaptive=regime_adaptive,
            regime_profiles=regime_profiles,
        )
        if mode == "BASE":
            chosen = base_cache_by_symbol[symbol]
        else:
            chosen = atr_metrics
        symbol_returns.append(chosen.total_return)
        total_trades += chosen.total_trades
        weighted_wins += (chosen.win_rate / 100.0) * chosen.total_trades

    portfolio_return = float(np.mean(symbol_returns)) if symbol_returns else 0.0
    weighted_win_rate = (weighted_wins / total_trades * 100.0) if total_trades else 0.0
    return PortfolioResult(
        name=label,
        portfolio_return=portfolio_return,
        total_trades=total_trades,
        weighted_win_rate=weighted_win_rate,
    )


def _build_candidates(params: StrategyParams, quick: bool) -> list[Candidate]:
    live_map = {
        "SAP.DE": (
            float(params.atr_dynamic_stop_mult),
            float(params.atr_dynamic_tp_r),
            float(params.atr_dynamic_be_r),
        ),
        "UNA.AS": (
            float(params.atr_dynamic_stop_mult),
            float(params.atr_dynamic_tp_r),
            float(params.atr_dynamic_be_r),
        ),
    }

    base_profiles = {
        "TREND_STRONG": (2.8, 4.5, 2.2),
        "TREND_NORMAL": (2.5, 4.0, 2.0),
        "CHOP_WEAK": (2.0, 3.0, 1.2),
    }
    strong_grid = [
        (2.6, 4.2, 2.0),
        (2.8, 4.5, 2.2),
        (3.0, 4.8, 2.4),
    ]
    normal_grid = [
        (2.3, 3.8, 1.8),
        (2.5, 4.0, 2.0),
        (2.7, 4.2, 2.2),
    ]
    weak_grid = [
        (1.8, 2.8, 1.0),
        (2.0, 3.0, 1.2),
        (2.2, 3.2, 1.4),
        (2.4, 3.4, 1.6),
    ]

    full: list[Candidate] = [
        Candidate(
            "LIVE_BASELINE",
            "NONE",
            0.00,
            live_map,
            False,
            dict(base_profiles),
        ),
        Candidate(
            "REGIME_BASE_PROFILE",
            "NONE",
            0.00,
            live_map,
            True,
            dict(base_profiles),
        ),
    ]

    idx = 0
    for strong in strong_grid:
        for normal in normal_grid:
            for weak in weak_grid:
                idx += 1
                profiles = {
                    "TREND_STRONG": strong,
                    "TREND_NORMAL": normal,
                    "CHOP_WEAK": weak,
                }
                full.append(
                    Candidate(
                        name=f"REGIME_G{idx:02d}",
                        entry_filter_mode="NONE",
                        entry_filter_param=0.00,
                        atr_map=live_map,
                        regime_adaptive=True,
                        regime_profiles=profiles,
                    )
                )

    if quick:
        return full[:10]
    return full


def main() -> None:
    params = StrategyParams()
    parser = argparse.ArgumentParser(description="Sweep strategy-upgrade candidates vs live hybrid baseline.")
    parser.add_argument("--days", type=int, default=730, help="Backtest lookback days (default: 730).")
    parser.add_argument("--fee-bps", type=float, default=0.0, help="Per-side fee in bps (default: 0.0).")
    parser.add_argument("--slippage-bps", type=float, default=2.0, help="Per-side slippage in bps (default: 2.0).")
    parser.add_argument(
        "--max-trades-per-day",
        type=int,
        default=9999,
        help="Max new entries per symbol per day (default: 9999).",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run reduced candidate set for faster iteration.",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=0,
        help="Optional cap on candidate count after generation (0 = no cap).",
    )
    args = parser.parse_args()

    symbol_mode_map = dict(params.symbol_strategy_mode)
    config = core.SimConfig(
        fee_bps=max(args.fee_bps, 0.0),
        slippage_bps=max(args.slippage_bps, 0.0),
        max_trades_per_day=max(args.max_trades_per_day, 1),
        atr_stop_multiplier=max(float(params.atr_dynamic_stop_mult), 0.1),
        atr_tp_r=max(float(params.atr_dynamic_tp_r), 0.1),
        atr_be_r=max(float(params.atr_dynamic_be_r), 0.1),
    )

    print(
        f"[INFO] Upgrade lab sweep | days={args.days} fee_bps={config.fee_bps:.2f} "
        f"slippage_bps={config.slippage_bps:.2f} max_trades={config.max_trades_per_day}"
    )
    print(f"[INFO] Hybrid modes: {symbol_mode_map}")
    bars_by_symbol = _load_bars(days=args.days)
    prepared_by_symbol = _prepare_indicator_frames(bars_by_symbol, ema_period=params.ema_period)

    # Optimization: reuse precomputed indicator frames in core simulation functions.
    core.add_indicators = lambda df_raw, ema_period: df_raw
    for symbol, bars in bars_by_symbol.items():
        source = "loaded" if not bars.empty else "missing"
        prepared_rows = len(prepared_by_symbol.get(symbol, pd.DataFrame()))
        print(f"[INFO] {symbol}: {source}, bars={len(bars)}, prepared={prepared_rows}")

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
        )

    candidates = _build_candidates(params, quick=args.quick)
    if args.max_candidates > 0:
        candidates = candidates[: max(args.max_candidates, 1)]
    print(f"[INFO] Candidate count: {len(candidates)}")
    results: list[PortfolioResult] = []
    for candidate in candidates:
        result = _simulate_portfolio(
            prepared_by_symbol=prepared_by_symbol,
            config=config,
            symbol_mode_map=symbol_mode_map,
            entry_filter_mode=candidate.entry_filter_mode,
            entry_filter_param=candidate.entry_filter_param,
            atr_map=candidate.atr_map,
            regime_adaptive=candidate.regime_adaptive,
            regime_profiles=candidate.regime_profiles,
            base_cache_by_symbol=base_cache_by_symbol,
            label=candidate.name,
        )
        results.append(result)
        print(
            f"[RUN] {candidate.name}: ret={result.portfolio_return:.2f}% "
            f"trades={result.total_trades} win={result.weighted_win_rate:.2f}%"
        , flush=True)

    baseline = next((r for r in results if r.name == "LIVE_BASELINE"), None)
    if baseline is None:
        raise RuntimeError("LIVE_BASELINE result missing.")

    ranked = sorted(results, key=lambda r: r.portfolio_return, reverse=True)
    print("\n" + "=" * 106)
    print("STRATEGY UPGRADE LAB SWEEP - RANKING")
    print("=" * 106)
    print(f"{'Rank':<6} {'Candidate':<24} {'Return%':>10} {'Delta vs Live%':>16} {'Trades':>10} {'WinRate%':>10}")
    print("-" * 106)
    for idx, row in enumerate(ranked, start=1):
        delta = row.portfolio_return - baseline.portfolio_return
        print(
            f"{idx:<6} {row.name:<24} {row.portfolio_return:>10.2f} {delta:>16.2f} "
            f"{row.total_trades:>10d} {row.weighted_win_rate:>10.2f}"
        )
    print("-" * 106)
    best = ranked[0]
    relation = "BETTER" if best.portfolio_return > baseline.portfolio_return else "WORSE_OR_EQUAL"
    print(
        f"[RESULT] Best candidate={best.name} return={best.portfolio_return:.2f}% | "
        f"live={baseline.portfolio_return:.2f}% | delta={best.portfolio_return - baseline.portfolio_return:.2f}% "
        f"=> {relation}"
    )
    print("=" * 106)


if __name__ == "__main__":
    main()
