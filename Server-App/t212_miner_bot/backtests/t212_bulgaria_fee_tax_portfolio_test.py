"""
Build and test best 5-stock baskets under Bulgaria/Trading212 cost assumptions.

Outputs:
- Best 5 stocks (global universe)
- Best 5 stocks (EU-only universe)
- Comparison vs current live basket

Strategy logic:
- Same 5m/15m signal stack and management flow as current T212 strategy code.
- For each symbol, tests BASE and ATR modes and keeps the better one.
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
from t212_miner_bot.config import SYMBOLS_MAP, StrategyParams


DATA_DIR = REPO_ROOT / "data"


# For EUR base account in Trading212 (Bulgaria):
# - Trading212 commission: 0
# - FX conversion fee: ~0.15% (15 bps) when instrument currency != EUR
# - UK stamp duty (stocks): 0.5% on buy -> modeled as +25 bps/side equivalent
# - France FTT (eligible shares): 0.3% on buy -> modeled as +15 bps/side equivalent
FX_BPS_PER_SIDE = 15.0
UK_STAMP_DUTY_EQUIV_BPS_PER_SIDE = 25.0
FRANCE_FTT_EQUIV_BPS_PER_SIDE = 15.0


EU_SUFFIXES = {".AS", ".DE", ".PA", ".CO"}
EUR_MARKET_SUFFIXES = {".AS", ".DE", ".PA"}


@dataclass(frozen=True)
class SymbolResult:
    symbol: str
    mode: str
    bars: int
    fee_bps_per_side: float
    total_return: float
    win_rate: float
    trades: int
    profit_factor: float


def _discover_symbol_files(data_dir: Path) -> dict[str, Path]:
    alias_map = {
        "SHEL.AS": "SHELL.AS",
        "SHEL": "SHELL.AS",
        "SAP": "SAP.DE",
        "ASML": "ASML.AS",
        "RIO": "RIO.L",
    }
    candidates = sorted(data_dir.glob("*_5m.csv"))
    out: dict[str, Path] = {}
    raw_has_exchange: dict[str, bool] = {}
    for path in candidates:
        stem = path.stem
        if not stem.endswith("_5m"):
            continue
        raw_symbol = stem[:-3]
        symbol = alias_map.get(raw_symbol, raw_symbol)
        if not symbol:
            continue
        current_has_exchange = "." in raw_symbol
        if symbol not in out:
            out[symbol] = path
            raw_has_exchange[symbol] = current_has_exchange
            continue
        # Keep exchange-qualified source file when both exist.
        if current_has_exchange and not raw_has_exchange.get(symbol, False):
            out[symbol] = path
            raw_has_exchange[symbol] = True
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


def _symbol_suffix(symbol: str) -> str:
    if "." not in symbol:
        return ""
    return "." + symbol.split(".", 1)[1].upper()


def _is_eu_symbol(symbol: str) -> bool:
    return _symbol_suffix(symbol) in EU_SUFFIXES


def _fee_bps_per_side_for_symbol(symbol: str) -> float:
    suffix = _symbol_suffix(symbol)
    fee_bps = 0.0

    # FX conversion for non-EUR markets.
    if suffix not in EUR_MARKET_SUFFIXES:
        fee_bps += FX_BPS_PER_SIDE

    # UK stamp duty equivalent.
    if suffix == ".L":
        fee_bps += UK_STAMP_DUTY_EQUIV_BPS_PER_SIDE

    # France FTT equivalent.
    if suffix == ".PA":
        fee_bps += FRANCE_FTT_EQUIV_BPS_PER_SIDE

    return fee_bps


def _format_pf(value: float) -> str:
    return f"{value:.2f}" if math.isfinite(value) else "inf"


def _simulate_symbol_best_mode(
    *,
    symbol: str,
    bars: pd.DataFrame,
    params: StrategyParams,
    slippage_bps: float,
    morning_map: dict[str, bool],
) -> tuple[SymbolResult | None, core.VariantMetrics | None, core.VariantMetrics | None]:
    if bars.empty:
        return None, None, None

    fee_bps = _fee_bps_per_side_for_symbol(symbol)
    config = core.SimConfig(
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        max_trades_per_day=9999,
        atr_stop_multiplier=max(float(params.atr_dynamic_stop_mult), 0.1),
        atr_tp_r=max(float(params.atr_dynamic_tp_r), 0.1),
        atr_be_r=max(float(params.atr_dynamic_be_r), 0.1),
        morning_protect_enabled=bool(params.morning_protect_enabled),
        morning_real_profit_trigger_pct=max(float(params.morning_real_profit_trigger_pct), 0.0),
        morning_profit_capture_pct=max(float(params.morning_profit_capture_pct), 0.0),
        morning_protect_window_minutes=max(int(params.morning_protect_window_minutes), 1),
        morning_protect_symbol_enabled=morning_map,
    )

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
    chosen = atr if atr.total_return > base.total_return else base
    mode = "ATR" if chosen is atr else "BASE"

    row = SymbolResult(
        symbol=symbol,
        mode=mode,
        bars=len(bars),
        fee_bps_per_side=fee_bps,
        total_return=chosen.total_return,
        win_rate=chosen.win_rate,
        trades=chosen.total_trades,
        profit_factor=chosen.profit_factor,
    )
    return row, base, atr


def _portfolio_summary(rows: list[SymbolResult]) -> tuple[float, int, float]:
    if not rows:
        return 0.0, 0, 0.0
    avg_ret = float(sum(r.total_return for r in rows) / len(rows))
    trades = sum(r.trades for r in rows)
    weighted_win = (
        sum((r.win_rate / 100.0) * r.trades for r in rows) / trades * 100.0 if trades > 0 else 0.0
    )
    return avg_ret, trades, weighted_win


def _print_basket(title: str, rows: list[SymbolResult]) -> None:
    print("\n" + "=" * 120)
    print(title)
    print("=" * 120)
    print(
        f"{'Symbol':<12} {'Mode':>6} {'Bars':>7} {'Fee bps/side':>13} "
        f"{'Return%':>10} {'Win%':>8} {'Trades':>8} {'PF':>8}"
    )
    print("-" * 120)
    for row in rows:
        print(
            f"{row.symbol:<12} {row.mode:>6} {row.bars:>7d} {row.fee_bps_per_side:>13.2f} "
            f"{row.total_return:>10.2f} {row.win_rate:>8.2f} {row.trades:>8d} {_format_pf(row.profit_factor):>8}"
        )
    avg_ret, trades, weighted_win = _portfolio_summary(rows)
    print("-" * 120)
    print(
        f"{'PORTFOLIO AVG':<12} {'-':>6} {'-':>7} {'-':>13} "
        f"{avg_ret:>10.2f} {weighted_win:>8.2f} {trades:>8d} {'-':>8}"
    )
    print("=" * 120)


def run(days: int, min_trades: int, slippage_bps: float, min_return_pct: float, min_pf: float) -> None:
    params = StrategyParams()
    symbol_files = _discover_symbol_files(DATA_DIR)
    symbols = sorted(symbol_files.keys())
    if not symbols:
        raise RuntimeError(f"No *_5m.csv files found in {DATA_DIR}")

    morning_map = {symbol: bool(params.morning_protect_symbol_enabled.get(symbol, False)) for symbol in symbols}

    print(
        f"[INFO] Bulgaria/Trading212 cost-aware portfolio test | days={days} symbols={len(symbols)} "
        f"min_trades={min_trades} slippage_bps={slippage_bps:.2f}"
    )
    print(
        "[INFO] Cost model: "
        "FX=15 bps/side for non-EUR, UK stamp duty=50 bps roundtrip equiv, "
        "France FTT=30 bps roundtrip equiv, Trading212 commission=0"
    )

    results: list[SymbolResult] = []
    mode_metrics_by_symbol: dict[str, dict[str, core.VariantMetrics]] = {}
    bars_count_by_symbol: dict[str, int] = {}
    fee_by_symbol: dict[str, float] = {}
    for symbol in symbols:
        bars = _load_csv(symbol_files[symbol], days=days)
        row, base_metrics, atr_metrics = _simulate_symbol_best_mode(
            symbol=symbol,
            bars=bars,
            params=params,
            slippage_bps=slippage_bps,
            morning_map=morning_map,
        )
        if row is None or base_metrics is None or atr_metrics is None:
            continue
        mode_metrics_by_symbol[symbol] = {"BASE": base_metrics, "ATR": atr_metrics}
        bars_count_by_symbol[symbol] = row.bars
        fee_by_symbol[symbol] = row.fee_bps_per_side
        if row.trades < min_trades:
            continue
        results.append(row)
        print(
            f"[RUN] {symbol:<12} mode={row.mode:<4} fee_bps={row.fee_bps_per_side:>5.1f} "
            f"ret={row.total_return:>8.2f}% trades={row.trades:>4d}"
        )

    if not results:
        raise RuntimeError("No symbols passed filters.")

    ranked = sorted(results, key=lambda r: r.total_return, reverse=True)
    eu_ranked = [r for r in ranked if _is_eu_symbol(r.symbol)]
    eligible = [r for r in ranked if r.total_return >= min_return_pct and r.profit_factor >= min_pf]
    eu_eligible = [r for r in eligible if _is_eu_symbol(r.symbol)]

    best5_all = eligible[:5]
    best5_eu = eu_eligible[:5]

    live_rows: list[SymbolResult] = []
    for symbol, live_mode in params.symbol_strategy_mode.items():
        mode = str(live_mode).strip().upper()
        if symbol not in mode_metrics_by_symbol:
            continue
        chosen = mode_metrics_by_symbol[symbol]["ATR" if mode == "ATR" else "BASE"]
        live_rows.append(
            SymbolResult(
                symbol=symbol,
                mode="ATR" if mode == "ATR" else "BASE",
                bars=bars_count_by_symbol.get(symbol, 0),
                fee_bps_per_side=fee_by_symbol.get(symbol, _fee_bps_per_side_for_symbol(symbol)),
                total_return=chosen.total_return,
                win_rate=chosen.win_rate,
                trades=chosen.total_trades,
                profit_factor=chosen.profit_factor,
            )
        )

    _print_basket("BEST 5 STOCKS (GLOBAL, COST-AWARE, FILTERED)", best5_all)
    _print_basket("BEST 5 STOCKS (EU ONLY, COST-AWARE, FILTERED)", best5_eu)
    _print_basket("CURRENT LIVE SYMBOL-MODE BASKET (COST-AWARE)", live_rows)

    all_ret, _, _ = _portfolio_summary(best5_all)
    eu_ret, _, _ = _portfolio_summary(best5_eu)
    live_ret, _, _ = _portfolio_summary(live_rows)

    print("\n" + "=" * 120)
    print("COMPARISON")
    print("=" * 120)
    print(
        f"Filters used: min_return={min_return_pct:.2f}% min_pf={min_pf:.2f} min_trades={min_trades}"
    )
    print(f"Eligible global symbols: {len(eligible)}")
    print(f"Eligible EU symbols: {len(eu_eligible)}")
    print(f"Live 4-stock avg return: {live_ret:.2f}%")
    print(f"Best 5 global avg return: {all_ret:.2f}% | Delta vs live: {all_ret - live_ret:.2f} pp")
    print(f"Best 5 EU avg return:     {eu_ret:.2f}% | Delta vs live: {eu_ret - live_ret:.2f} pp")
    if len(best5_all) < 5:
        print(f"[WARN] Global basket has only {len(best5_all)} symbols after filters.")
    if len(best5_eu) < 5:
        print(f"[WARN] EU basket has only {len(best5_eu)} symbols after filters.")
    print("=" * 120)


def main() -> None:
    parser = argparse.ArgumentParser(description="Find best 5 global/EU stocks with Bulgaria T212 costs.")
    parser.add_argument("--days", type=int, default=730, help="Backtest lookback days (default: 730).")
    parser.add_argument("--min-trades", type=int, default=80, help="Minimum trades filter (default: 80).")
    parser.add_argument(
        "--slippage-bps",
        type=float,
        default=5.0,
        help="Per-side slippage bps (default: 5.0).",
    )
    parser.add_argument(
        "--min-return-pct",
        type=float,
        default=0.0,
        help="Minimum symbol return threshold after costs (default: 0.0).",
    )
    parser.add_argument(
        "--min-pf",
        type=float,
        default=1.0,
        help="Minimum symbol profit factor threshold (default: 1.0).",
    )
    args = parser.parse_args()
    run(
        days=max(args.days, 30),
        min_trades=max(args.min_trades, 0),
        slippage_bps=max(args.slippage_bps, 0.0),
        min_return_pct=float(args.min_return_pct),
        min_pf=max(float(args.min_pf), 0.0),
    )


if __name__ == "__main__":
    main()
