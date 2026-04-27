"""
Out-of-sample robustness check for best-5 tuned candidate parameters.

Compares:
- CURRENT_LIVE params
- FULL_GRID_TUNED candidate params

Across calendar windows on local 5m data with Bulgaria/Trading212 cost model.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
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


WINDOWS: list[tuple[str, pd.Timestamp, pd.Timestamp]] = [
    ("2024", pd.Timestamp("2024-01-01T00:00:00Z"), pd.Timestamp("2024-12-31T23:59:59Z")),
    ("2025", pd.Timestamp("2025-01-01T00:00:00Z"), pd.Timestamp("2025-12-31T23:59:59Z")),
    ("2026_YTD", pd.Timestamp("2026-01-01T00:00:00Z"), pd.Timestamp("2026-12-31T23:59:59Z")),
]


SYMBOLS = ["SAP.DE", "ASML.AS", "UNA.AS", "AMD", "SHELL.AS"]


def _load_all_bars(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    if not required.issubset(set(df.columns)):
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    out = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out = out.dropna(subset=["timestamp", "open", "high", "low", "close"]).sort_values("timestamp")
    out = out.set_index("timestamp")
    return out


def _simulate(
    *,
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


def _fmt(v: float) -> str:
    return f"{v:.2f}" if math.isfinite(v) else "inf"


def run(slippage_bps: float, max_trades_per_day: int) -> None:
    params = StrategyParams()
    files = _discover_symbol_files(DATA_DIR)

    live_map: dict[str, SymbolCfg] = {
        "SAP.DE": SymbolCfg(
            mode="ATR",
            profit_lock_trigger_pct=float(params.profit_lock_trigger_pct),
            profit_lock_stop_pct=float(params.profit_lock_stop_pct),
            morning_enabled=True,
            morning_real_profit_trigger_pct=float(params.morning_real_profit_trigger_pct),
            morning_profit_capture_pct=float(params.morning_profit_capture_pct),
            morning_window_minutes=int(params.morning_protect_window_minutes),
            atr_stop_mult=float(params.atr_dynamic_stop_mult),
            atr_tp_r=float(params.atr_dynamic_tp_r),
            atr_be_r=float(params.atr_dynamic_be_r),
        ),
        "ASML.AS": SymbolCfg(
            mode="BASE",
            profit_lock_trigger_pct=float(params.profit_lock_trigger_pct),
            profit_lock_stop_pct=float(params.profit_lock_stop_pct),
            morning_enabled=True,
            morning_real_profit_trigger_pct=float(params.morning_real_profit_trigger_pct),
            morning_profit_capture_pct=float(params.morning_profit_capture_pct),
            morning_window_minutes=int(params.morning_protect_window_minutes),
            atr_stop_mult=float(params.atr_dynamic_stop_mult),
            atr_tp_r=float(params.atr_dynamic_tp_r),
            atr_be_r=float(params.atr_dynamic_be_r),
        ),
        "UNA.AS": SymbolCfg(
            mode="BASE",
            profit_lock_trigger_pct=float(params.profit_lock_trigger_pct),
            profit_lock_stop_pct=float(params.profit_lock_stop_pct),
            morning_enabled=False,
            morning_real_profit_trigger_pct=float(params.morning_real_profit_trigger_pct),
            morning_profit_capture_pct=float(params.morning_profit_capture_pct),
            morning_window_minutes=int(params.morning_protect_window_minutes),
            atr_stop_mult=float(params.atr_dynamic_stop_mult),
            atr_tp_r=float(params.atr_dynamic_tp_r),
            atr_be_r=float(params.atr_dynamic_be_r),
        ),
        "AMD": SymbolCfg(
            mode="BASE",
            profit_lock_trigger_pct=float(params.profit_lock_trigger_pct),
            profit_lock_stop_pct=float(params.profit_lock_stop_pct),
            morning_enabled=False,
            morning_real_profit_trigger_pct=float(params.morning_real_profit_trigger_pct),
            morning_profit_capture_pct=float(params.morning_profit_capture_pct),
            morning_window_minutes=int(params.morning_protect_window_minutes),
            atr_stop_mult=float(params.atr_dynamic_stop_mult),
            atr_tp_r=float(params.atr_dynamic_tp_r),
            atr_be_r=float(params.atr_dynamic_be_r),
        ),
        "SHELL.AS": SymbolCfg(
            mode="BASE",
            profit_lock_trigger_pct=float(params.profit_lock_trigger_pct),
            profit_lock_stop_pct=float(params.profit_lock_stop_pct),
            morning_enabled=False,
            morning_real_profit_trigger_pct=float(params.morning_real_profit_trigger_pct),
            morning_profit_capture_pct=float(params.morning_profit_capture_pct),
            morning_window_minutes=int(params.morning_protect_window_minutes),
            atr_stop_mult=float(params.atr_dynamic_stop_mult),
            atr_tp_r=float(params.atr_dynamic_tp_r),
            atr_be_r=float(params.atr_dynamic_be_r),
        ),
    }

    tuned_map: dict[str, SymbolCfg] = {
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
        "ASML.AS": live_map["ASML.AS"],
        "UNA.AS": SymbolCfg(
            mode="BASE",
            profit_lock_trigger_pct=0.03,
            profit_lock_stop_pct=0.018,
            morning_enabled=False,
            morning_real_profit_trigger_pct=0.01,
            morning_profit_capture_pct=0.25,
            morning_window_minutes=120,
            atr_stop_mult=2.5,
            atr_tp_r=4.0,
            atr_be_r=1.8,
        ),
        "AMD": SymbolCfg(
            mode="BASE",
            profit_lock_trigger_pct=0.04,
            profit_lock_stop_pct=0.018,
            morning_enabled=False,
            morning_real_profit_trigger_pct=0.01,
            morning_profit_capture_pct=0.25,
            morning_window_minutes=120,
            atr_stop_mult=2.5,
            atr_tp_r=4.0,
            atr_be_r=1.8,
        ),
        "SHELL.AS": live_map["SHELL.AS"],
    }

    raw_by_symbol: dict[str, pd.DataFrame] = {}
    for symbol in SYMBOLS:
        if symbol not in files:
            raise RuntimeError(f"Missing CSV for {symbol}")
        raw = _load_all_bars(files[symbol])
        if raw.empty:
            raise RuntimeError(f"No bars loaded for {symbol}")
        raw_by_symbol[symbol] = raw

    prepared_by_symbol: dict[str, pd.DataFrame] = {}
    for symbol, raw in raw_by_symbol.items():
        prepared = core.add_indicators(raw, ema_period=params.ema_period).dropna().copy()
        prepared_by_symbol[symbol] = prepared
    core.add_indicators = lambda df_raw, ema_period: df_raw

    print(
        f"[INFO] OOS candidate check | slippage_bps={slippage_bps:.2f} max_trades_per_day={max_trades_per_day}"
    )
    print(f"[INFO] Symbols: {', '.join(SYMBOLS)}")
    print(f"[INFO] Windows: {', '.join(w[0] for w in WINDOWS)}")

    deltas: list[float] = []
    print("\n" + "=" * 120)
    print("WINDOW SUMMARY (LIVE vs TUNED)")
    print("=" * 120)
    print(
        f"{'Window':<10} {'Live Avg%':>10} {'Tuned Avg%':>11} {'Delta pp':>10} "
        f"{'Live Trades':>12} {'Tuned Trades':>13}"
    )
    print("-" * 120)

    for window_name, start, end in WINDOWS:
        live_rets: list[float] = []
        tuned_rets: list[float] = []
        live_trades = 0
        tuned_trades = 0
        for symbol in SYMBOLS:
            bars_all = prepared_by_symbol[symbol]
            bars = bars_all[(bars_all.index >= start) & (bars_all.index <= end)].copy()
            if bars.empty:
                continue

            live_metrics = _simulate(
                symbol=symbol,
                bars=bars,
                cfg=live_map[symbol],
                slippage_bps=slippage_bps,
                max_trades_per_day=max_trades_per_day,
            )
            tuned_metrics = _simulate(
                symbol=symbol,
                bars=bars,
                cfg=tuned_map[symbol],
                slippage_bps=slippage_bps,
                max_trades_per_day=max_trades_per_day,
            )
            live_rets.append(live_metrics.total_return)
            tuned_rets.append(tuned_metrics.total_return)
            live_trades += int(live_metrics.total_trades)
            tuned_trades += int(tuned_metrics.total_trades)

        live_avg = sum(live_rets) / len(live_rets) if live_rets else 0.0
        tuned_avg = sum(tuned_rets) / len(tuned_rets) if tuned_rets else 0.0
        delta = tuned_avg - live_avg
        deltas.append(delta)
        print(
            f"{window_name:<10} {live_avg:>10.2f} {tuned_avg:>11.2f} {delta:>10.2f} "
            f"{live_trades:>12d} {tuned_trades:>13d}"
        )

    print("-" * 120)
    print(f"{'Average delta':<10} {'':>10} {'':>11} {sum(deltas)/len(deltas):>10.2f}")
    print("=" * 120)

    print("\nPer-symbol 2025 check (most complete OOS year):")
    print(
        f"{'Symbol':<11} {'Live Ret%':>10} {'Tuned Ret%':>11} {'Delta pp':>10} "
        f"{'Live Trades':>12} {'Tuned Trades':>13}"
    )
    print("-" * 120)
    start_2025 = pd.Timestamp("2025-01-01T00:00:00Z")
    end_2025 = pd.Timestamp("2025-12-31T23:59:59Z")
    for symbol in SYMBOLS:
        bars_all = prepared_by_symbol[symbol]
        bars = bars_all[(bars_all.index >= start_2025) & (bars_all.index <= end_2025)].copy()
        live_metrics = _simulate(
            symbol=symbol,
            bars=bars,
            cfg=live_map[symbol],
            slippage_bps=slippage_bps,
            max_trades_per_day=max_trades_per_day,
        )
        tuned_metrics = _simulate(
            symbol=symbol,
            bars=bars,
            cfg=tuned_map[symbol],
            slippage_bps=slippage_bps,
            max_trades_per_day=max_trades_per_day,
        )
        print(
            f"{symbol:<11} {live_metrics.total_return:>10.2f} {tuned_metrics.total_return:>11.2f} "
            f"{(tuned_metrics.total_return - live_metrics.total_return):>10.2f} "
            f"{live_metrics.total_trades:>12d} {tuned_metrics.total_trades:>13d}"
        )
    print("-" * 120)


def main() -> None:
    parser = argparse.ArgumentParser(description="OOS check for full-grid tuned best-5 candidate.")
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    parser.add_argument("--max-trades-per-day", type=int, default=9999)
    args = parser.parse_args()
    run(
        slippage_bps=max(float(args.slippage_bps), 0.0),
        max_trades_per_day=max(int(args.max_trades_per_day), 1),
    )


if __name__ == "__main__":
    main()
