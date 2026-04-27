"""
Stock-universe sweep for current T212 5m/15m strategy logic.

Evaluates each locally available *_5m.csv symbol with:
- BASE mode simulation
- ATR mode simulation

Then ranks symbols by selected mode:
- best: choose better of BASE/ATR per symbol
- base: force BASE
- atr: force ATR
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
from t212_miner_bot.config import StrategyParams

DATA_DIR = REPO_ROOT / "data"


@dataclass(frozen=True)
class StockRow:
    symbol: str
    bars: int
    base_return: float
    atr_return: float
    selected_mode: str
    selected_return: float
    selected_win_rate: float
    selected_trades: int
    selected_pf: float


def _discover_symbol_files(data_dir: Path) -> dict[str, Path]:
    candidates = sorted(data_dir.glob("*_5m.csv"))
    out: dict[str, Path] = {}
    for path in candidates:
        stem = path.stem
        if not stem.endswith("_5m"):
            continue
        symbol = stem[:-3]
        if not symbol:
            continue
        # Prefer exchange-qualified symbol files (e.g., SAP.DE_5m over SAP_5m).
        if symbol in out and "." not in symbol:
            continue
        out[symbol] = path
    return out


def _load_csv(path: Path, days: int) -> pd.DataFrame:
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
    out = out.set_index("timestamp")
    if out.empty:
        return out

    end = pd.Timestamp.now(tz="UTC")
    start = end - pd.Timedelta(days=days)
    sliced = out[(out.index >= start) & (out.index <= end)].copy()
    return sliced if not sliced.empty else out


def _format_pf(value: float) -> str:
    return f"{value:.2f}" if math.isfinite(value) else "inf"


def run_sweep(days: int, selection_mode: str, min_trades: int, top_n: int) -> None:
    params = StrategyParams()
    symbol_files = _discover_symbol_files(DATA_DIR)
    if not symbol_files:
        raise RuntimeError(f"No *_5m.csv files found in {DATA_DIR}")

    symbols = sorted(symbol_files.keys())
    # For non-live symbols, keep morning-protect disabled by default.
    effective_morning_map = {
        symbol: bool(params.morning_protect_symbol_enabled.get(symbol, False))
        for symbol in symbols
    }
    config = core.SimConfig(
        fee_bps=0.0,
        slippage_bps=5.0,
        max_trades_per_day=9999,
        atr_stop_multiplier=max(float(params.atr_dynamic_stop_mult), 0.1),
        atr_tp_r=max(float(params.atr_dynamic_tp_r), 0.1),
        atr_be_r=max(float(params.atr_dynamic_be_r), 0.1),
        morning_protect_enabled=bool(params.morning_protect_enabled),
        morning_real_profit_trigger_pct=max(float(params.morning_real_profit_trigger_pct), 0.0),
        morning_profit_capture_pct=max(float(params.morning_profit_capture_pct), 0.0),
        morning_protect_window_minutes=max(int(params.morning_protect_window_minutes), 1),
        morning_protect_symbol_enabled=effective_morning_map,
    )

    print(
        f"[INFO] Universe sweep start | days={days} symbols={len(symbols)} "
        f"selection_mode={selection_mode} min_trades={min_trades}"
    )
    print(
        "[INFO] Shared params: "
        f"profit_lock_trigger={params.profit_lock_trigger_pct:.4f} "
        f"profit_lock_stop={params.profit_lock_stop_pct:.4f} "
        f"morning_enabled={params.morning_protect_enabled}"
    )

    rows: list[StockRow] = []
    for symbol in symbols:
        bars = _load_csv(symbol_files[symbol], days=days)
        if bars.empty:
            continue
        base = core._simulate_symbol_variant(
            bars,
            symbol=symbol,
            enable_break_even_1pct=False,
            config=config,
            entry_filter_mode="NONE",
            entry_filter_param=0.0,
            profit_lock_trigger_pct=float(params.profit_lock_trigger_pct),
            profit_lock_stop_pct=float(params.profit_lock_stop_pct),
        )
        atr = core._simulate_atr_dynamic_variant(
            bars,
            symbol=symbol,
            config=config,
            stop_mult=float(params.atr_dynamic_stop_mult),
            tp_r=float(params.atr_dynamic_tp_r),
            be_r=float(params.atr_dynamic_be_r),
            entry_filter_mode="NONE",
            entry_filter_param=0.0,
            regime_adaptive=False,
            profit_lock_trigger_pct=float(params.profit_lock_trigger_pct),
            profit_lock_stop_pct=float(params.profit_lock_stop_pct),
        )

        if selection_mode == "base":
            mode = "BASE"
            chosen = base
        elif selection_mode == "atr":
            mode = "ATR"
            chosen = atr
        else:
            if atr.total_return > base.total_return:
                mode = "ATR"
                chosen = atr
            else:
                mode = "BASE"
                chosen = base

        rows.append(
            StockRow(
                symbol=symbol,
                bars=len(bars),
                base_return=base.total_return,
                atr_return=atr.total_return,
                selected_mode=mode,
                selected_return=chosen.total_return,
                selected_win_rate=chosen.win_rate,
                selected_trades=chosen.total_trades,
                selected_pf=chosen.profit_factor,
            )
        )

    filtered = [r for r in rows if r.selected_trades >= min_trades]
    ranked = sorted(filtered, key=lambda x: x.selected_return, reverse=True)

    print("\n" + "=" * 138)
    print("T212 STOCK UNIVERSE SWEEP (CURRENT 5m/15m STRATEGY)")
    print("=" * 138)
    print(
        f"{'Rank':<6} {'Symbol':<12} {'Bars':>7} {'BASE Ret%':>10} {'ATR Ret%':>10} "
        f"{'Chosen':>8} {'Chosen Ret%':>12} {'Win%':>8} {'Trades':>8} {'PF':>8}"
    )
    print("-" * 138)
    for idx, row in enumerate(ranked[: max(top_n, 1)], start=1):
        print(
            f"{idx:<6} {row.symbol:<12} {row.bars:>7d} {row.base_return:>10.2f} {row.atr_return:>10.2f} "
            f"{row.selected_mode:>8} {row.selected_return:>12.2f} {row.selected_win_rate:>8.2f} "
            f"{row.selected_trades:>8d} {_format_pf(row.selected_pf):>8}"
        )
    print("-" * 138)
    if ranked:
        best = ranked[0]
        print(
            f"[RESULT] Best symbol={best.symbol} mode={best.selected_mode} "
            f"ret={best.selected_return:.2f}% trades={best.selected_trades} win={best.selected_win_rate:.2f}%"
        )
    else:
        print("[RESULT] No symbols passed filters.")
    print("=" * 138)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep local stock universe with current T212 5m/15m logic.")
    parser.add_argument("--days", type=int, default=730, help="Backtest lookback days (default: 730).")
    parser.add_argument(
        "--selection-mode",
        type=str,
        default="best",
        choices=["best", "base", "atr"],
        help="How to rank each stock: best mode, base only, or atr only.",
    )
    parser.add_argument(
        "--min-trades",
        type=int,
        default=80,
        help="Minimum selected-mode trades required to keep a stock (default: 80).",
    )
    parser.add_argument("--top-n", type=int, default=25, help="Rows to print (default: 25).")
    args = parser.parse_args()
    run_sweep(
        days=max(args.days, 30),
        selection_mode=str(args.selection_mode).strip().lower(),
        min_trades=max(args.min_trades, 0),
        top_n=max(args.top_n, 1),
    )


if __name__ == "__main__":
    main()
