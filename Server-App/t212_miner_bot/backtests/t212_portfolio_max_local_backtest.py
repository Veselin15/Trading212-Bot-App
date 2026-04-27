from __future__ import annotations

import argparse
import math
import sys
from dataclasses import replace
from pathlib import Path
from typing import Iterable

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from t212_miner_bot.backtests.t212_strategy_compare_4stocks import (  # noqa: E402
    SimConfig,
    VariantMetrics,
    _simulate_atr_dynamic_variant,
    _simulate_symbol_variant,
)
from t212_miner_bot.config import SYMBOLS_MAP, StrategyParams, TOTAL_PORTFOLIO_EUR  # noqa: E402


def _read_local_5m_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Normalize column names (some exports use Title Case OHLCV columns).
    df.columns = [str(c).strip() for c in df.columns]
    lower_map = {str(c).strip().lower(): c for c in df.columns}

    def _col(*names: str) -> str | None:
        for n in names:
            key = n.lower()
            if key in lower_map:
                return lower_map[key]
        return None

    ts_col = _col("timestamp", "datetime", "time")
    if ts_col is None:
        raise ValueError(f"{path}: expected a time column (timestamp/datetime/time).")

    o_col = _col("open")
    h_col = _col("high")
    l_col = _col("low")
    c_col = _col("close")
    v_col = _col("volume", "vol")

    required = {"open": o_col, "high": h_col, "low": l_col, "close": c_col, "volume": v_col}
    missing = [k for k, v in required.items() if v is None]
    if missing:
        raise ValueError(f"{path}: missing columns for: {', '.join(missing)}")

    ts = pd.to_datetime(df[ts_col], utc=True, errors="coerce")

    out = pd.DataFrame(
        {
            "timestamp": ts,
            "open": pd.to_numeric(df[o_col], errors="coerce"),
            "high": pd.to_numeric(df[h_col], errors="coerce"),
            "low": pd.to_numeric(df[l_col], errors="coerce"),
            "close": pd.to_numeric(df[c_col], errors="coerce"),
            "volume": pd.to_numeric(df[v_col], errors="coerce"),
        }
    )
    out = out.dropna(subset=["timestamp", "open", "high", "low", "close"]).sort_values("timestamp")
    out = out.set_index("timestamp")
    return out


def _candidate_paths(symbol: str) -> list[Path]:
    data_dir = REPO_ROOT / "data"
    # Prefer extended histories when present.
    names: list[str] = [
        f"{symbol}_5m_extended.csv",
        f"{symbol}_5m.csv",
    ]
    # Compatibility naming for some shells / older exports.
    if symbol == "ASML.AS":
        names.extend(["ASML_5m.csv"])
    if symbol == "SAP.DE":
        names.extend(["SAP_5m.csv"])

    out: list[Path] = []
    for n in names:
        p = data_dir / n
        if p.exists():
            out.append(p)
    return out


def load_longest_local_bars(symbol: str) -> tuple[pd.DataFrame, Path]:
    best: tuple[pd.Timestamp, pd.Timestamp, int, Path, pd.DataFrame] | None = None
    for path in _candidate_paths(symbol):
        bars = _read_local_5m_csv(path)
        if bars.empty:
            continue
        start = pd.Timestamp(bars.index.min())
        end = pd.Timestamp(bars.index.max())
        rows = int(len(bars))
        score = (start, -rows)  # earliest start wins; tie-breaker: more rows
        cand = (start, end, rows, path, bars)
        if best is None or score < (best[0], -best[2]):
            best = cand
    if best is None:
        raise FileNotFoundError(f"No local 5m CSV found for {symbol} under {REPO_ROOT / 'data'}.")
    return best[4], best[3]


def simulate_live_hybrid(
    *,
    bars: pd.DataFrame,
    symbol: str,
    params: StrategyParams,
    sim: SimConfig,
    symbol_mode_map: dict[str, str],
) -> VariantMetrics:
    mode = str(symbol_mode_map.get(symbol, "BASE")).strip().upper()
    base = _simulate_symbol_variant(
        bars,
        symbol,
        enable_break_even_1pct=False,
        config=sim,
        entry_filter_atr_mult=0.0,
        profit_lock_trigger_pct=float(params.profit_lock_trigger_pct),
        profit_lock_stop_pct=float(params.profit_lock_stop_pct),
    )
    atr = _simulate_atr_dynamic_variant(
        bars,
        symbol,
        config=sim,
        entry_filter_atr_mult=0.0,
        profit_lock_trigger_pct=float(params.profit_lock_trigger_pct),
        profit_lock_stop_pct=float(params.profit_lock_stop_pct),
    )
    return base if mode == "BASE" else atr


def main(argv: Iterable[str] | None = None) -> None:
    params = StrategyParams()
    parser = argparse.ArgumentParser(
        description=(
            "Equal-weight portfolio backtest using the longest available local 5m CSVs "
            "and the same hybrid routing as t212_strategy_compare_4stocks (BASE vs ATR per symbol)."
        )
    )
    parser.add_argument(
        "--fee-bps",
        type=float,
        default=0.0,
        help="Per-side fee in bps (default: 0.0).",
    )
    parser.add_argument(
        "--slippage-bps",
        type=float,
        default=5.0,
        help="Per-side slippage in bps (default: 5.0).",
    )
    parser.add_argument(
        "--max-trades-per-day",
        type=int,
        default=9999,
        help="Max new entries per symbol per day (default: 9999).",
    )
    parser.add_argument(
        "--symbol-modes",
        type=str,
        default="",
        help="Optional per-symbol mode map, e.g. ASML.AS=BASE,SAP.DE=ATR,UNA.AS=ATR,AMD=BASE",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    def _parse_symbol_mode_map(raw: str) -> dict[str, str]:
        out: dict[str, str] = {}
        if not raw.strip():
            return out
        for part in raw.split(","):
            part = part.strip()
            if not part or "=" not in part:
                continue
            sym, mode = part.split("=", 1)
            sym = sym.strip()
            mode = mode.strip().upper()
            if sym:
                out[sym] = mode
        return out

    symbol_mode_map = _parse_symbol_mode_map(args.symbol_modes) or dict(params.symbol_strategy_mode)

    sim = SimConfig(
        fee_bps=max(float(args.fee_bps), 0.0),
        slippage_bps=max(float(args.slippage_bps), 0.0),
        max_trades_per_day=max(int(args.max_trades_per_day), 1),
        atr_stop_multiplier=float(params.atr_dynamic_stop_mult),
        atr_tp_r=float(params.atr_dynamic_tp_r),
        atr_be_r=float(params.atr_dynamic_be_r),
        morning_protect_enabled=bool(params.morning_protect_enabled),
        morning_real_profit_trigger_pct=float(params.morning_real_profit_trigger_pct),
        morning_profit_capture_pct=float(params.morning_profit_capture_pct),
        morning_protect_window_minutes=int(params.morning_protect_window_minutes),
        morning_protect_symbol_enabled=dict(params.morning_protect_symbol_enabled),
        atr_trail_mult=float(params.atr_trail_mult),
    )

    symbols = list(SYMBOLS_MAP.keys())
    per_symbol: dict[str, tuple[VariantMetrics, Path, pd.Timestamp, pd.Timestamp]] = {}

    print(f"[INFO] Universe={', '.join(symbols)}")
    print(f"[INFO] Hybrid modes={symbol_mode_map}")
    print(
        "[INFO] Costs: "
        f"fee_bps={sim.fee_bps:.2f} slippage_bps={sim.slippage_bps:.2f} "
        f"max_trades_per_day={sim.max_trades_per_day}"
    )

    returns: list[float] = []
    for symbol in symbols:
        bars, path = load_longest_local_bars(symbol)
        m = simulate_live_hybrid(
            bars=bars,
            symbol=symbol,
            params=params,
            sim=sim,
            symbol_mode_map=symbol_mode_map,
        )
        start = pd.Timestamp(bars.index.min())
        end = pd.Timestamp(bars.index.max())
        per_symbol[symbol] = (m, path, start, end)
        returns.append(float(m.total_return))
        print(
            f"[OK] {symbol}: file={path.name} bars={len(bars)} "
            f"range={start.isoformat()}..{end.isoformat()} "
            f"ret%={m.total_return:.2f} trades={m.total_trades} win%={m.win_rate:.2f} mode={symbol_mode_map.get(symbol)}"
        )

    portfolio_return_pct = float(sum(returns) / max(len(returns), 1))
    notional_each = float(TOTAL_PORTFOLIO_EUR) / max(len(symbols), 1)
    portfolio_profit_eur = notional_each * sum(r / 100.0 for r in returns)

    print("\n" + "=" * 110)
    print("PORTFOLIO SUMMARY (equal-notional sleeves, long-only signal engine)")
    print("=" * 110)
    print(f"[INFO] TOTAL_PORTFOLIO_EUR={TOTAL_PORTFOLIO_EUR:.2f} (split equally across {len(symbols)} symbols)")
    print(f"[INFO] Portfolio return (avg of per-symbol return%%): {portfolio_return_pct:.2f}%")
    print(f"[INFO] Portfolio profit EUR (sum of per-symbol PnL on each {notional_each:.2f} EUR sleeve): {portfolio_profit_eur:.2f} EUR")
    if any(math.isinf(m[0].profit_factor) for m in per_symbol.values()):
        print("[INFO] Note: at least one symbol has infinite profit factor (no losing trades).")

    # Portfolio-level min start / max end for transparency.
    min_start = min(t[2] for t in per_symbol.values())
    max_end = max(t[3] for t in per_symbol.values())
    print(f"[INFO] Combined calendar span (min start -> max end): {min_start.isoformat()}..{max_end.isoformat()}")


if __name__ == "__main__":
    main()
