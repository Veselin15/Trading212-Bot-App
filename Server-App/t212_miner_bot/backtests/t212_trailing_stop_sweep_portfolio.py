"""
Sweep BASE-mode runner ATR trailing multiplier and evaluate the current live basket.

Goal
- Keep signals and management logic identical to the live bot/backtest core
- Only vary the BASE runner trailing stop multiplier used after Unit1 TP (Unit2 trail)

Notes
- Uses locally available CSV data in /data. For your current live basket, the max available
  history is determined by those files (often ~2024-2026 for EU names).
- Costs modeled similarly to Bulgaria/Trading212 assumptions:
  - FX 15 bps/side for non-EUR instruments (e.g. AMD)
  - Slippage configured via CLI (default 5 bps/side)
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
class SymbolRun:
    symbol: str
    mode: str
    fee_bps_per_side: float
    bars: int
    start: str
    end: str
    total_return: float
    trades: int
    win_rate: float
    profit_factor: float


def _symbol_suffix(symbol: str) -> str:
    if "." not in symbol:
        return ""
    return "." + symbol.split(".", 1)[1].upper()


EUR_MARKET_SUFFIXES = {".AS", ".DE", ".PA"}
FX_BPS_PER_SIDE = 15.0


def _fee_bps_per_side(symbol: str) -> float:
    suffix = _symbol_suffix(symbol)
    if suffix in EUR_MARKET_SUFFIXES:
        return 0.0
    return FX_BPS_PER_SIDE


def _load_best_csv(symbol: str, days: int) -> pd.DataFrame:
    candidates = [
        DATA_DIR / f"{symbol}_5m_5year.csv",
        DATA_DIR / f"{symbol}_5m_extended.csv",
        DATA_DIR / f"{symbol}_5m.csv",
    ]
    source: Path | None = None
    for p in candidates:
        if p.exists() and p.stat().st_size > 100_000:
            source = p
            break
    if source is None:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    df = pd.read_csv(source)
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    if not required.issubset(set(df.columns)):
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    out = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out = out.dropna(subset=["timestamp", "open", "high", "low", "close"]).sort_values("timestamp")
    out = out.set_index("timestamp")
    if out.empty:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    end = pd.Timestamp.now(tz="UTC")
    start = end - pd.Timedelta(days=days)
    sliced = out[(out.index >= start) & (out.index <= end)].copy()
    return sliced if not sliced.empty else out[["open", "high", "low", "close", "volume"]].copy()


def _format_pf(value: float) -> str:
    return f"{value:.2f}" if math.isfinite(value) else "inf"


def _simulate_symbol(
    *,
    symbol: str,
    mode: str,
    bars: pd.DataFrame,
    params: StrategyParams,
    slippage_bps: float,
    atr_trail_mult: float,
) -> SymbolRun | None:
    if bars.empty:
        return None
    fee_bps = _fee_bps_per_side(symbol)
    cfg = core.SimConfig(
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        max_trades_per_day=9999,
        atr_stop_multiplier=max(float(params.atr_dynamic_stop_mult), 0.1),
        atr_tp_r=max(float(params.atr_dynamic_tp_r), 0.1),
        atr_be_r=max(float(params.atr_dynamic_be_r), 0.1),
        atr_trail_mult=max(float(atr_trail_mult), 0.1),
        morning_protect_enabled=bool(params.morning_protect_enabled),
        morning_real_profit_trigger_pct=max(float(params.morning_real_profit_trigger_pct), 0.0),
        morning_profit_capture_pct=max(float(params.morning_profit_capture_pct), 0.0),
        morning_protect_window_minutes=max(int(params.morning_protect_window_minutes), 1),
        morning_protect_symbol_enabled=dict(params.morning_protect_symbol_enabled),
    )

    mode_u = str(mode).strip().upper()
    if mode_u == "ATR":
        stop_mult, tp_r, be_r = params.atr_dynamic_params_by_symbol.get(
            symbol,
            (params.atr_dynamic_stop_mult, params.atr_dynamic_tp_r, params.atr_dynamic_be_r),
        )
        m = core._simulate_atr_dynamic_variant(
            bars,
            symbol=symbol,
            config=cfg,
            stop_mult=float(stop_mult),
            tp_r=float(tp_r),
            be_r=float(be_r),
            entry_filter_mode="NONE",
            entry_filter_param=0.0,
            regime_adaptive=False,
            profit_lock_trigger_pct=float(params.profit_lock_by_symbol.get(symbol, (params.profit_lock_trigger_pct, params.profit_lock_stop_pct))[0]),
            profit_lock_stop_pct=float(params.profit_lock_by_symbol.get(symbol, (params.profit_lock_trigger_pct, params.profit_lock_stop_pct))[1]),
        )
    else:
        trig, stop = params.profit_lock_by_symbol.get(symbol, (params.profit_lock_trigger_pct, params.profit_lock_stop_pct))
        m = core._simulate_symbol_variant(
            bars,
            symbol=symbol,
            enable_break_even_1pct=False,
            config=cfg,
            entry_filter_mode="NONE",
            entry_filter_param=0.0,
            profit_lock_trigger_pct=float(trig),
            profit_lock_stop_pct=float(stop),
        )

    start = str(bars.index.min().date()) if len(bars.index) else "n/a"
    end = str(bars.index.max().date()) if len(bars.index) else "n/a"
    return SymbolRun(
        symbol=symbol,
        mode=mode_u,
        fee_bps_per_side=fee_bps,
        bars=len(bars),
        start=start,
        end=end,
        total_return=float(m.total_return),
        trades=int(m.total_trades),
        win_rate=float(m.win_rate),
        profit_factor=float(m.profit_factor),
    )


def run(days: int, slippage_bps: float, trail_mults: list[float]) -> None:
    params = StrategyParams()
    basket = list(params.symbol_strategy_mode.items())
    if not basket:
        raise RuntimeError("No symbols configured in StrategyParams.symbol_strategy_mode")

    print(
        f"[INFO] Trailing sweep | days={days} | slippage_bps={slippage_bps:.2f} | "
        f"basket={', '.join([f'{s}={m}' for s,m in basket])}"
    )
    print("[INFO] Trailing parameter swept: SimConfig.atr_trail_mult (BASE runner only, Unit2 after Unit1 TP).")

    best: tuple[float, float] | None = None  # (avg_ret, trail_mult)
    table: list[tuple[float, float, int]] = []

    for tm in trail_mults:
        rows: list[SymbolRun] = []
        for sym, mode in basket:
            bars = _load_best_csv(sym, days=days)
            row = _simulate_symbol(
                symbol=sym,
                mode=mode,
                bars=bars,
                params=params,
                slippage_bps=slippage_bps,
                atr_trail_mult=float(tm),
            )
            if row is not None:
                rows.append(row)
        if not rows:
            continue
        avg_ret = float(sum(r.total_return for r in rows) / len(rows))
        trades = int(sum(r.trades for r in rows))
        table.append((avg_ret, float(tm), trades))
        if best is None or avg_ret > best[0]:
            best = (avg_ret, float(tm))

    if not table:
        raise RuntimeError("No results produced. Are the CSVs present?")

    table.sort(key=lambda x: x[0], reverse=True)
    print("\n" + "=" * 110)
    print("PORTFOLIO (AVG RETURN %) BY TRAIL MULTIPLIER")
    print("=" * 110)
    print(f"{'trail_mult':>10} {'avg_return%':>12} {'total_trades':>13}")
    print("-" * 110)
    for avg_ret, tm, trades in table:
        print(f"{tm:>10.2f} {avg_ret:>12.2f} {trades:>13d}")
    print("=" * 110)

    assert best is not None
    best_ret, best_tm = best
    print(f"\n[OK] BEST: atr_trail_mult={best_tm:.2f} -> portfolio avg return={best_ret:.2f}%")


def _parse_mults(raw: str) -> list[float]:
    out: list[float] = []
    for part in raw.split(","):
        p = part.strip()
        if not p:
            continue
        try:
            out.append(float(p))
        except ValueError:
            continue
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep trailing ATR multiplier for current live basket.")
    parser.add_argument("--days", type=int, default=730, help="Lookback days (default: 730).")
    parser.add_argument("--slippage-bps", type=float, default=5.0, help="Per-side slippage bps (default: 5).")
    parser.add_argument(
        "--trail-mults",
        type=str,
        default="1.5,2.0,2.5,3.0,3.5,4.0",
        help="Comma-separated trail multipliers to test (default: 1.5..4.0 step 0.5).",
    )
    args = parser.parse_args()
    mults = _parse_mults(args.trail_mults)
    if not mults:
        raise SystemExit("No valid --trail-mults provided.")
    run(days=max(int(args.days), 30), slippage_bps=max(float(args.slippage_bps), 0.0), trail_mults=mults)


if __name__ == "__main__":
    main()

