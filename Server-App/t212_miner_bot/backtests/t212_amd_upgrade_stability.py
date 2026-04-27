"""
Stability-first AMD upgrade analysis.

Compares:
- Current live basket configuration
- AMD custom parameter variants
- Candidate replacement symbols for AMD

Evaluation windows:
- 2024
- 2025
- 2026 YTD
"""

from __future__ import annotations

import argparse
import math
import statistics
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
)
from t212_miner_bot.config import StrategyParams


DATA_DIR = REPO_ROOT / "data"

WINDOWS: list[tuple[str, pd.Timestamp, pd.Timestamp]] = [
    ("2024", pd.Timestamp("2024-01-01T00:00:00Z"), pd.Timestamp("2024-12-31T23:59:59Z")),
    ("2025", pd.Timestamp("2025-01-01T00:00:00Z"), pd.Timestamp("2025-12-31T23:59:59Z")),
    ("2026_YTD", pd.Timestamp("2026-01-01T00:00:00Z"), pd.Timestamp("2026-12-31T23:59:59Z")),
]

BASE_CORE = ["ASML.AS", "SAP.DE", "UNA.AS"]


@dataclass(frozen=True)
class SymbolCfg:
    mode: str
    profit_lock_trigger_pct: float
    profit_lock_stop_pct: float
    morning_enabled: bool
    morning_real_profit_trigger_pct: float
    morning_profit_capture_pct: float
    morning_window_minutes: int
    atr_stop_mult: float
    atr_tp_r: float
    atr_be_r: float


@dataclass(frozen=True)
class BasketVariant:
    name: str
    fourth_symbol: str
    symbol_cfgs: dict[str, SymbolCfg]


def _load_csv(path: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
    except Exception:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    if not required.issubset(set(df.columns)):
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    out = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out = out.dropna(subset=["timestamp", "open", "high", "low", "close"]).sort_values("timestamp")
    return out.set_index("timestamp")


def _simulate_symbol(
    symbol: str,
    bars: pd.DataFrame,
    cfg: SymbolCfg,
    slippage_bps: float,
    max_trades_per_day: int,
) -> core.VariantMetrics:
    fee_bps = _fee_bps_per_side_for_symbol(symbol)
    sim_cfg = core.SimConfig(
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        max_trades_per_day=max_trades_per_day,
        atr_stop_multiplier=cfg.atr_stop_mult,
        atr_tp_r=cfg.atr_tp_r,
        atr_be_r=cfg.atr_be_r,
        morning_protect_enabled=cfg.morning_enabled,
        morning_real_profit_trigger_pct=cfg.morning_real_profit_trigger_pct,
        morning_profit_capture_pct=cfg.morning_profit_capture_pct,
        morning_protect_window_minutes=cfg.morning_window_minutes,
        morning_protect_symbol_enabled={symbol: cfg.morning_enabled},
    )
    if cfg.mode.upper() == "ATR":
        return core._simulate_atr_dynamic_variant(
            bars,
            symbol=symbol,
            config=sim_cfg,
            stop_mult=cfg.atr_stop_mult,
            tp_r=cfg.atr_tp_r,
            be_r=cfg.atr_be_r,
            entry_filter_mode="NONE",
            entry_filter_param=0.0,
            regime_adaptive=False,
            profit_lock_trigger_pct=cfg.profit_lock_trigger_pct,
            profit_lock_stop_pct=cfg.profit_lock_stop_pct,
        )
    return core._simulate_symbol_variant(
        bars,
        symbol=symbol,
        enable_break_even_1pct=False,
        config=sim_cfg,
        entry_filter_mode="NONE",
        entry_filter_param=0.0,
        profit_lock_trigger_pct=cfg.profit_lock_trigger_pct,
        profit_lock_stop_pct=cfg.profit_lock_stop_pct,
    )


def _score(window_returns: list[float]) -> float:
    if not window_returns:
        return -1e9
    avg = sum(window_returns) / len(window_returns)
    std = statistics.pstdev(window_returns) if len(window_returns) > 1 else 0.0
    worst = min(window_returns)
    # Stability-first objective.
    return avg - (0.40 * std) + (0.20 * worst)


def _cfg_key(cfg: SymbolCfg) -> tuple:
    return (
        cfg.mode,
        round(cfg.profit_lock_trigger_pct, 6),
        round(cfg.profit_lock_stop_pct, 6),
        int(cfg.morning_enabled),
        round(cfg.morning_real_profit_trigger_pct, 6),
        round(cfg.morning_profit_capture_pct, 6),
        int(cfg.morning_window_minutes),
        round(cfg.atr_stop_mult, 6),
        round(cfg.atr_tp_r, 6),
        round(cfg.atr_be_r, 6),
    )


def _build_base_cfgs(params: StrategyParams) -> dict[str, SymbolCfg]:
    return {
        "ASML.AS": SymbolCfg(
            mode="BASE",
            profit_lock_trigger_pct=0.034,
            profit_lock_stop_pct=0.014,
            morning_enabled=True,
            morning_real_profit_trigger_pct=0.01,
            morning_profit_capture_pct=0.25,
            morning_window_minutes=120,
            atr_stop_mult=float(params.atr_dynamic_stop_mult),
            atr_tp_r=float(params.atr_dynamic_tp_r),
            atr_be_r=float(params.atr_dynamic_be_r),
        ),
        "SAP.DE": SymbolCfg(
            mode="ATR",
            profit_lock_trigger_pct=0.034,
            profit_lock_stop_pct=0.014,
            morning_enabled=True,
            morning_real_profit_trigger_pct=0.01,
            morning_profit_capture_pct=0.35,
            morning_window_minutes=120,
            atr_stop_mult=2.5,
            atr_tp_r=5.0,
            atr_be_r=1.2,
        ),
        "UNA.AS": SymbolCfg(
            mode="BASE",
            profit_lock_trigger_pct=0.034,
            profit_lock_stop_pct=0.014,
            morning_enabled=False,
            morning_real_profit_trigger_pct=0.01,
            morning_profit_capture_pct=0.25,
            morning_window_minutes=120,
            atr_stop_mult=float(params.atr_dynamic_stop_mult),
            atr_tp_r=float(params.atr_dynamic_tp_r),
            atr_be_r=float(params.atr_dynamic_be_r),
        ),
    }


def _fmt(v: float) -> str:
    return f"{v:.2f}" if math.isfinite(v) else "inf"


def run(slippage_bps: float, max_trades_per_day: int, quick: bool) -> None:
    params = StrategyParams()
    symbol_files = _discover_symbol_files(DATA_DIR)
    if not symbol_files:
        raise RuntimeError("No symbol files found.")

    raw_bars: dict[str, pd.DataFrame] = {}
    for symbol, path in symbol_files.items():
        bars = _load_csv(path)
        if not bars.empty:
            raw_bars[symbol] = bars

    needed_symbols = set(BASE_CORE + ["AMD", "SHELL.AS"])
    if not needed_symbols.issubset(set(raw_bars.keys())):
        missing = sorted(needed_symbols - set(raw_bars.keys()))
        raise RuntimeError(f"Missing required symbols in data: {missing}")

    prepared_bars: dict[str, pd.DataFrame] = {}
    for symbol, bars in raw_bars.items():
        prepared = core.add_indicators(bars, ema_period=params.ema_period).dropna().copy()
        if not prepared.empty:
            prepared_bars[symbol] = prepared
    core.add_indicators = lambda df_raw, ema_period: df_raw

    base_cfgs = _build_base_cfgs(params)

    # Current live AMD profile.
    amd_current = SymbolCfg(
        mode="BASE",
        profit_lock_trigger_pct=0.04,
        profit_lock_stop_pct=0.018,
        morning_enabled=False,
        morning_real_profit_trigger_pct=0.01,
        morning_profit_capture_pct=0.25,
        morning_window_minutes=120,
        atr_stop_mult=float(params.atr_dynamic_stop_mult),
        atr_tp_r=float(params.atr_dynamic_tp_r),
        atr_be_r=float(params.atr_dynamic_be_r),
    )

    variants: list[BasketVariant] = []
    variants.append(
        BasketVariant(
            name="LIVE_AMD_CURRENT",
            fourth_symbol="AMD",
            symbol_cfgs={**base_cfgs, "AMD": amd_current},
        )
    )

    # AMD tuning grid.
    if quick:
        trigger_values = [0.034, 0.04, 0.045]
        stop_values = [0.014, 0.018]
        atr_stop_values = [2.5]
        atr_tp_values = [4.0, 5.0]
        atr_be_values = [1.2, 1.8]
    else:
        trigger_values = [0.03, 0.034, 0.04, 0.045]
        stop_values = [0.014, 0.018, 0.022]
        atr_stop_values = [2.2, 2.5]
        atr_tp_values = [4.0, 5.0]
        atr_be_values = [1.2, 1.8]
    for mode in ["BASE", "ATR"]:
        for trig, stop in product(trigger_values, stop_values):
            if stop >= trig:
                continue
            if mode == "ATR":
                for a_stop, a_tp, a_be in product(atr_stop_values, atr_tp_values, atr_be_values):
                    cfg = SymbolCfg(
                        mode=mode,
                        profit_lock_trigger_pct=trig,
                        profit_lock_stop_pct=stop,
                        morning_enabled=False,
                        morning_real_profit_trigger_pct=0.01,
                        morning_profit_capture_pct=0.25,
                        morning_window_minutes=120,
                        atr_stop_mult=a_stop,
                        atr_tp_r=a_tp,
                        atr_be_r=a_be,
                    )
                    variants.append(
                        BasketVariant(
                            name=f"AMD_{mode}_t{trig:.3f}_s{stop:.3f}_atr{a_stop:.1f}_{a_tp:.1f}_{a_be:.1f}",
                            fourth_symbol="AMD",
                            symbol_cfgs={**base_cfgs, "AMD": cfg},
                        )
                    )
            else:
                cfg = SymbolCfg(
                    mode=mode,
                    profit_lock_trigger_pct=trig,
                    profit_lock_stop_pct=stop,
                    morning_enabled=False,
                    morning_real_profit_trigger_pct=0.01,
                    morning_profit_capture_pct=0.25,
                    morning_window_minutes=120,
                    atr_stop_mult=float(params.atr_dynamic_stop_mult),
                    atr_tp_r=float(params.atr_dynamic_tp_r),
                    atr_be_r=float(params.atr_dynamic_be_r),
                )
                variants.append(
                    BasketVariant(
                        name=f"AMD_{mode}_t{trig:.3f}_s{stop:.3f}",
                        fourth_symbol="AMD",
                        symbol_cfgs={**base_cfgs, "AMD": cfg},
                    )
                )

    # Replacement candidates: evaluate symbols with enough bars (excluding base core + AMD).
    if quick:
        replacement_pool = [s for s in ["SHELL.AS", "TSLA", "NFLX", "AAPL"] if s in prepared_bars]
    else:
        replacement_pool = []
        for symbol, bars in prepared_bars.items():
            if symbol in set(BASE_CORE + ["AMD"]):
                continue
            if len(bars) >= 10_000:
                replacement_pool.append(symbol)
        replacement_pool = sorted(replacement_pool)[:12]
    for symbol in replacement_pool:
        for mode in ["BASE", "ATR"]:
            cfg = SymbolCfg(
                mode=mode,
                profit_lock_trigger_pct=0.034,
                profit_lock_stop_pct=0.014,
                morning_enabled=False,
                morning_real_profit_trigger_pct=0.01,
                morning_profit_capture_pct=0.25,
                morning_window_minutes=120,
                atr_stop_mult=float(params.atr_dynamic_stop_mult),
                atr_tp_r=float(params.atr_dynamic_tp_r),
                atr_be_r=float(params.atr_dynamic_be_r),
            )
            variants.append(
                BasketVariant(
                    name=f"REPLACE_{symbol}_{mode}",
                    fourth_symbol=symbol,
                    symbol_cfgs={**base_cfgs, symbol: cfg},
                )
            )

    print(
        f"[INFO] AMD stability study | variants={len(variants)} "
        f"replacements_tested={len(replacement_pool)}"
    )

    # Precompute core 3-symbol contribution once for each window.
    core_sum_by_window: dict[str, float] = {}
    core_count_by_window: dict[str, int] = {}
    for window_name, start, end in WINDOWS:
        core_sum = 0.0
        core_count = 0
        for symbol in BASE_CORE:
            bars_all = prepared_bars[symbol]
            bars = bars_all[(bars_all.index >= start) & (bars_all.index <= end)].copy()
            if bars.empty:
                continue
            metrics = _simulate_symbol(
                symbol=symbol,
                bars=bars,
                cfg=base_cfgs[symbol],
                slippage_bps=slippage_bps,
                max_trades_per_day=max_trades_per_day,
            )
            core_sum += float(metrics.total_return)
            core_count += 1
        core_sum_by_window[window_name] = core_sum
        core_count_by_window[window_name] = core_count

    symbol_window_cache: dict[tuple[str, str, tuple], float] = {}

    ranked_rows: list[dict[str, float | str]] = []
    total_variants = len(variants)
    for idx, variant in enumerate(variants, start=1):
        if idx == 1 or idx % 10 == 0 or idx == total_variants:
            print(f"[RUN] {idx}/{total_variants} {variant.name}", flush=True)
        window_returns: list[float] = []
        for window_name, start, end in WINDOWS:
            symbol = variant.fourth_symbol
            cfg = variant.symbol_cfgs[symbol]
            cache_key = (window_name, symbol, _cfg_key(cfg))
            if cache_key in symbol_window_cache:
                fourth_ret = symbol_window_cache[cache_key]
            else:
                bars_all = prepared_bars[symbol]
                bars = bars_all[(bars_all.index >= start) & (bars_all.index <= end)].copy()
                if bars.empty:
                    fourth_ret = 0.0
                else:
                    fourth_ret = float(
                        _simulate_symbol(
                            symbol=symbol,
                            bars=bars,
                            cfg=cfg,
                            slippage_bps=slippage_bps,
                            max_trades_per_day=max_trades_per_day,
                        ).total_return
                    )
                symbol_window_cache[cache_key] = fourth_ret

            denom = core_count_by_window.get(window_name, 0) + 1
            if denom <= 0:
                window_returns.append(0.0)
            else:
                total_ret = core_sum_by_window.get(window_name, 0.0) + fourth_ret
                window_returns.append(total_ret / denom)

        ranked_rows.append(
            {
                "name": variant.name,
                "fourth_symbol": variant.fourth_symbol,
                "ret_2024": window_returns[0],
                "ret_2025": window_returns[1],
                "ret_2026": window_returns[2],
                "avg_ret": sum(window_returns) / len(window_returns),
                "worst_ret": min(window_returns),
                "score": _score(window_returns),
            }
        )

    ranked = sorted(ranked_rows, key=lambda r: float(r["score"]), reverse=True)
    print("\nTop 12 stability-ranked variants:")
    print("-" * 140)
    print(
        f"{'Rank':<5} {'Variant':<56} {'4th':<10} {'2024%':>8} {'2025%':>8} {'2026%':>8} "
        f"{'Avg%':>8} {'Worst%':>8} {'Score':>8}"
    )
    print("-" * 140)
    for idx, row in enumerate(ranked[:12], start=1):
        print(
            f"{idx:<5} {str(row['name'])[:56]:<56} {str(row['fourth_symbol']):<10} "
            f"{_fmt(float(row['ret_2024'])):>8} {_fmt(float(row['ret_2025'])):>8} {_fmt(float(row['ret_2026'])):>8} "
            f"{_fmt(float(row['avg_ret'])):>8} {_fmt(float(row['worst_ret'])):>8} {_fmt(float(row['score'])):>8}"
        )
    print("-" * 140)

    live_row = next((r for r in ranked if r["name"] == "LIVE_AMD_CURRENT"), None)
    best_row = ranked[0] if ranked else None
    if live_row and best_row:
        print(
            f"[RESULT] Best variant={best_row['name']} | avg={_fmt(float(best_row['avg_ret']))}% "
            f"worst={_fmt(float(best_row['worst_ret']))}% | "
            f"delta_vs_live_avg={_fmt(float(best_row['avg_ret']) - float(live_row['avg_ret']))} pp"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="AMD upgrade stability sweep and replacement test.")
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    parser.add_argument("--max-trades-per-day", type=int, default=9999)
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run reduced AMD/replacement search set for faster turnaround.",
    )
    args = parser.parse_args()
    run(
        slippage_bps=max(float(args.slippage_bps), 0.0),
        max_trades_per_day=max(int(args.max_trades_per_day), 1),
        quick=bool(args.quick),
    )


if __name__ == "__main__":
    main()
