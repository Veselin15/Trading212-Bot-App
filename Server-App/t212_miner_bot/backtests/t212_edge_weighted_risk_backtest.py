"""
2-year test for Edge-Weighted Risk (EWR) allocation on the current T212 live strategy.

Compares:
- Baseline: equal-weight basket return per month
- EWR: monthly symbol weights adjusted by recent edge score

Notes:
- This keeps the existing per-symbol strategy logic unchanged.
- The new logic acts at portfolio-allocation layer (risk budget per symbol).
"""

from __future__ import annotations

import argparse
import math
import statistics
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from t212_miner_bot.backtests import t212_strategy_compare_4stocks as core
from t212_miner_bot.backtests.t212_bulgaria_fee_tax_portfolio_test import _fee_bps_per_side_for_symbol
from t212_miner_bot.config import StrategyParams


DATA_DIR = REPO_ROOT / "data"


def _load_symbol_5m(symbol: str) -> pd.DataFrame:
    candidates = [DATA_DIR / f"{symbol}_5m.csv"]
    if symbol == "SHELL.AS":
        candidates.append(DATA_DIR / "SHEL.AS_5m.csv")
    source = next((p for p in candidates if p.exists()), None)
    if source is None:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.read_csv(source)
    required = {"timestamp", "open", "high", "low", "close", "volume"}
    if not required.issubset(df.columns):
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    out = df[["timestamp", "open", "high", "low", "close", "volume"]].copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out = out.dropna(subset=["timestamp", "open", "high", "low", "close"]).sort_values("timestamp")
    return out.set_index("timestamp")


def _symbol_profit_lock(params: StrategyParams, symbol: str) -> tuple[float, float]:
    by_symbol = getattr(params, "profit_lock_by_symbol", {})
    if isinstance(by_symbol, dict) and symbol in by_symbol:
        raw = by_symbol[symbol]
        if isinstance(raw, (tuple, list)) and len(raw) >= 2:
            return max(float(raw[0]), 0.0), max(float(raw[1]), 0.0)
    return max(float(params.profit_lock_trigger_pct), 0.0), max(float(params.profit_lock_stop_pct), 0.0)


def _symbol_atr_params(params: StrategyParams, symbol: str) -> tuple[float, float, float]:
    by_symbol = getattr(params, "atr_dynamic_params_by_symbol", {})
    if isinstance(by_symbol, dict) and symbol in by_symbol:
        raw = by_symbol[symbol]
        if isinstance(raw, (tuple, list)) and len(raw) >= 3:
            return max(float(raw[0]), 0.1), max(float(raw[1]), 0.1), max(float(raw[2]), 0.1)
    return (
        max(float(params.atr_dynamic_stop_mult), 0.1),
        max(float(params.atr_dynamic_tp_r), 0.1),
        max(float(params.atr_dynamic_be_r), 0.1),
    )


def _symbol_morning_map(params: StrategyParams, symbols: list[str]) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for s in symbols:
        out[s] = bool(params.morning_protect_symbol_enabled.get(s, False))
    return out


def _simulate_month(symbol: str, bars: pd.DataFrame, params: StrategyParams, slippage_bps: float) -> tuple[float, int]:
    if bars.empty:
        return 0.0, 0
    fee_bps = _fee_bps_per_side_for_symbol(symbol)
    morning_map = _symbol_morning_map(params, [symbol])
    stop_mult, tp_r, be_r = _symbol_atr_params(params, symbol)
    lock_trigger, lock_stop = _symbol_profit_lock(params, symbol)
    cfg = core.SimConfig(
        fee_bps=fee_bps,
        slippage_bps=slippage_bps,
        max_trades_per_day=9999,
        atr_stop_multiplier=stop_mult,
        atr_tp_r=tp_r,
        atr_be_r=be_r,
        morning_protect_enabled=bool(params.morning_protect_enabled),
        morning_real_profit_trigger_pct=max(float(params.morning_real_profit_trigger_pct), 0.0),
        morning_profit_capture_pct=max(float(params.morning_profit_capture_pct), 0.0),
        morning_protect_window_minutes=max(int(params.morning_protect_window_minutes), 1),
        morning_protect_symbol_enabled=morning_map,
    )
    mode = str(params.symbol_strategy_mode.get(symbol, "BASE")).strip().upper()
    if mode == "ATR":
        m = core._simulate_atr_dynamic_variant(
            bars,
            symbol=symbol,
            config=cfg,
            stop_mult=stop_mult,
            tp_r=tp_r,
            be_r=be_r,
            entry_filter_mode="NONE",
            entry_filter_param=0.0,
            regime_adaptive=False,
            profit_lock_trigger_pct=lock_trigger,
            profit_lock_stop_pct=lock_stop,
        )
    else:
        m = core._simulate_symbol_variant(
            bars,
            symbol=symbol,
            enable_break_even_1pct=False,
            config=cfg,
            entry_filter_mode="NONE",
            entry_filter_param=0.0,
            profit_lock_trigger_pct=lock_trigger,
            profit_lock_stop_pct=lock_stop,
        )
    return float(m.total_return), int(m.total_trades)


def _edge_weights(
    history: dict[str, list[float]],
    symbols: list[str],
    *,
    z_alpha: float,
    min_mult: float,
    max_mult: float,
    min_samples: int,
) -> dict[str, float]:
    # Use recent monthly return mean-variance score:
    # score = mean - 0.5 * std, then clamp relative multipliers [0.6, 1.4], normalize.
    scores: dict[str, float] = {}
    for s in symbols:
        h = history.get(s, [])
        if len(h) < min_samples:
            scores[s] = 0.0
            continue
        mean_r = sum(h) / len(h)
        std_r = statistics.pstdev(h) if len(h) > 1 else 0.0
        scores[s] = mean_r - (0.5 * std_r)

    values = list(scores.values())
    mu = sum(values) / len(values) if values else 0.0
    sigma = (statistics.pstdev(values) if len(values) > 1 else 1.0) or 1.0
    multipliers: dict[str, float] = {}
    for s in symbols:
        z = (scores[s] - mu) / sigma
        mult = 1.0 + (z_alpha * z)
        multipliers[s] = min(max_mult, max(min_mult, mult))

    total = sum(multipliers.values())
    if total <= 0:
        return {s: 1.0 / len(symbols) for s in symbols}
    return {s: multipliers[s] / total for s in symbols}


def run(
    days: int,
    slippage_bps: float,
    lookback_months: int,
    *,
    z_alpha: float = 0.20,
    min_mult: float = 0.60,
    max_mult: float = 1.40,
    min_samples: int = 2,
    verbose: bool = True,
) -> dict[str, float]:
    params = StrategyParams()
    symbols = list(params.symbol_strategy_mode.keys())
    raw: dict[str, pd.DataFrame] = {s: _load_symbol_5m(s) for s in symbols}
    if any(df.empty for df in raw.values()):
        missing = [s for s, df in raw.items() if df.empty]
        raise RuntimeError(f"Missing/empty local data for symbols: {missing}")

    # Use common date range and 2-year slice.
    max_end = min(df.index.max() for df in raw.values())
    start = max_end - pd.Timedelta(days=days)
    sliced = {s: df[(df.index >= start) & (df.index <= max_end)].copy() for s, df in raw.items()}

    # Monthly windows.
    first_month = min(df.index.min() for df in sliced.values()).tz_localize(None).to_period("M")
    last_month = max(df.index.max() for df in sliced.values()).tz_localize(None).to_period("M")
    months = pd.period_range(first_month, last_month, freq="M")

    baseline_equity = 1.0
    ewr_equity = 1.0
    history: dict[str, list[float]] = {s: [] for s in symbols}
    rows: list[dict[str, float | str]] = []

    for m in months:
        m_start = pd.Timestamp(m.start_time, tz="UTC")
        m_end = pd.Timestamp(m.end_time, tz="UTC")
        month_ret: dict[str, float] = {}
        for s in symbols:
            bars = sliced[s][(sliced[s].index >= m_start) & (sliced[s].index <= m_end)].copy()
            ret, _ = _simulate_month(s, bars, params, slippage_bps=slippage_bps)
            month_ret[s] = ret

        equal_r = sum(month_ret.values()) / len(symbols)
        baseline_equity *= (1.0 + equal_r / 100.0)

        weights = _edge_weights(
            {s: history[s][-lookback_months:] for s in symbols},
            symbols=symbols,
            z_alpha=z_alpha,
            min_mult=min_mult,
            max_mult=max_mult,
            min_samples=min_samples,
        )
        ewr_r = sum(weights[s] * month_ret[s] for s in symbols)
        ewr_equity *= (1.0 + ewr_r / 100.0)

        for s in symbols:
            history[s].append(month_ret[s])

        rows.append(
            {
                "month": str(m),
                "baseline_ret_pct": equal_r,
                "ewr_ret_pct": ewr_r,
                "delta_pp": ewr_r - equal_r,
                "w_ASML.AS": weights.get("ASML.AS", 0.0),
                "w_SAP.DE": weights.get("SAP.DE", 0.0),
                "w_UNA.AS": weights.get("UNA.AS", 0.0),
                "w_AMD": weights.get("AMD", 0.0),
            }
        )

    baseline_total = (baseline_equity - 1.0) * 100.0
    ewr_total = (ewr_equity - 1.0) * 100.0
    delta = ewr_total - baseline_total

    df_out = pd.DataFrame(rows)
    if verbose:
        print(
            f"[INFO] EWR backtest complete | months={len(df_out)} days={days} "
            f"lookback_months={lookback_months} slippage_bps={slippage_bps:.2f} "
            f"z_alpha={z_alpha:.3f} min_mult={min_mult:.2f} max_mult={max_mult:.2f} min_samples={min_samples}"
        )
        print(f"[RESULT] Baseline total return: {baseline_total:.2f}%")
        print(f"[RESULT] EWR total return:      {ewr_total:.2f}%")
        print(f"[RESULT] Delta vs baseline:     {delta:.2f} pp")
        print("\nLatest 8 months:")
        print(df_out.tail(8).to_string(index=False))
    return {
        "baseline_total": baseline_total,
        "ewr_total": ewr_total,
        "delta_pp": delta,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Edge-weighted risk 2-year backtest.")
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--slippage-bps", type=float, default=5.0)
    parser.add_argument("--lookback-months", type=int, default=3)
    parser.add_argument("--z-alpha", type=float, default=0.20)
    parser.add_argument("--min-mult", type=float, default=0.60)
    parser.add_argument("--max-mult", type=float, default=1.40)
    parser.add_argument("--min-samples", type=int, default=2)
    args = parser.parse_args()
    run(
        days=max(int(args.days), 120),
        slippage_bps=max(float(args.slippage_bps), 0.0),
        lookback_months=max(int(args.lookback_months), 1),
        z_alpha=max(float(args.z_alpha), 0.0),
        min_mult=max(float(args.min_mult), 0.1),
        max_mult=max(float(args.max_mult), max(float(args.min_mult), 0.1)),
        min_samples=max(int(args.min_samples), 1),
    )


if __name__ == "__main__":
    main()
