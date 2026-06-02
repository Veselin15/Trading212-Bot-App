"""
5-Year Global Portfolio Simulation
====================================

Runs the full historical dataset (≈5 years) through the production portfolio
engine and reports in-sample vs out-of-sample performance.

Supports two strategy modes:
  --v1   Classic SwingStrategy (v1, baseline)
  --v2   SwingStrategyV2 (default) with:
           - Earlier trail activation (1.5R)
           - Volatility spike filter
           - RSI quality gate
           - Asymmetric time exit

Portfolio risk guards (v2 mode):
  - PortfolioHeatGuard: daily 2 % circuit breaker
  - DrawdownPositionScaler: reduce size in 3 tiers of drawdown

Important: The saved models were trained on the first ~4 years of data.
  - First 4 years → in-sample  (model saw this data)
  - Last  1 year  → out-of-sample  (true generalization benchmark)

Usage
-----
  python -m t212_miner_bot.five_year_portfolio_sim          # v2 (default)
  python -m t212_miner_bot.five_year_portfolio_sim --v1     # v1 baseline
"""

from __future__ import annotations

import logging
import time
from typing import Dict, Optional, Tuple

import pandas as pd

from t212_miner_bot.config import (
    EU_SYMBOLS,
    TRAIN_END,
    TEST_START,
    INITIAL_CAPITAL,
    SYMBOL_THRESHOLDS,
    PYRAMID_ATR_MULT,
    PYRAMID_FRACTION,
    PYRAMID_SYMBOLS,
    MACRO_BULL_RISK_SCALE,
    MACRO_BEAR_RISK_SCALE,
    MACRO_REGIME_BULL_THRESHOLD,
)
from t212_miner_bot.data_loader import get_available_symbols, load_multi_timeframe
from t212_miner_bot.features import (
    compute_all_features,
    compute_sector_relative_strength,
    attach_sector_rs,
    get_feature_columns,
)
from t212_miner_bot.ensemble_model import EnsembleModel
from t212_miner_bot.strategy import SwingStrategy
from t212_miner_bot.strategy import SwingStrategyV2
from t212_miner_bot.backtest import BacktestEngine
from t212_miner_bot.portfolio_risk import PortfolioHeatGuard, DrawdownPositionScaler


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def _prepare_full_data(symbols: list[str]) -> Dict[str, pd.DataFrame]:
    raw_15m: Dict[str, pd.DataFrame] = {}
    raw_5m: Dict[str, Optional[pd.DataFrame]] = {}

    log.info("Loading OHLCV for %d symbols…", len(symbols))
    for sym in symbols:
        try:
            data = load_multi_timeframe(sym)
            raw_15m[sym] = data["15m"]
            raw_5m[sym] = data.get("5m")
        except Exception as exc:
            log.warning("  [%s] skip (load): %s", sym, exc)

    if not raw_15m:
        raise RuntimeError("No symbols loaded from data/")

    log.info("Computing sector RS across universe…")
    sector_rs = compute_sector_relative_strength(raw_15m)

    log.info("Computing features (15m + 5m) for each symbol…")
    full_data: Dict[str, pd.DataFrame] = {}
    for sym, df15 in raw_15m.items():
        df = df15.copy()
        try:
            compute_all_features(df, raw_5m.get(sym), symbol=sym)
            attach_sector_rs(df, sector_rs.get(sym))
            # Ensure feature columns exist and fill NaNs
            fcols = [c for c in get_feature_columns(df) if c in df.columns]
            valid = [c for c in fcols if not df[c].isna().all()]
            df[valid] = df[valid].fillna(0.0)
            full_data[sym] = df
        except Exception as exc:
            log.warning("  [%s] skip (features): %s", sym, exc)

    return full_data


def _score_all(full_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.Series]:
    log.info("Loading models and scoring (once)…")
    proba_cache: Dict[str, pd.Series] = {}
    for sym, df in full_data.items():
        try:
            model = EnsembleModel.load(sym)
            fcols = [c for c in get_feature_columns(df) if c in df.columns and not df[c].isna().all()]
            X = df[fcols].fillna(0.0)
            proba_cache[sym] = pd.Series(model.predict_proba(X), index=df.index)
        except Exception as exc:
            log.warning("  [%s] model/score missing: %s", sym, exc)
    return proba_cache


def _run_engine(
    data_slice: Dict[str, pd.DataFrame],
    proba_cache: Dict[str, pd.Series],
    initial_capital: float,
    use_v2: bool = True,
) -> Tuple[pd.DataFrame, Dict]:
    if use_v2:
        strategy = SwingStrategyV2()
        heat_guard = PortfolioHeatGuard()
        dd_scaler  = DrawdownPositionScaler()
    else:
        strategy   = SwingStrategy()   # v1 baseline
        heat_guard = None
        dd_scaler  = None

    engine = BacktestEngine(
        strategy=strategy,
        initial_capital=initial_capital,
        pyramid_enabled=True,
        pyramid_atr_mult=PYRAMID_ATR_MULT,
        pyramid_fraction=PYRAMID_FRACTION,
        pyramid_symbols=PYRAMID_SYMBOLS,
        risk_scale=MACRO_BULL_RISK_SCALE,
        sector_clamping_enabled=True,
        dynamic_macro_risk_enabled=True,
        macro_regime_bull_threshold=MACRO_REGIME_BULL_THRESHOLD,
        macro_bull_risk_scale=MACRO_BULL_RISK_SCALE,
        macro_bear_risk_scale=MACRO_BEAR_RISK_SCALE,
        portfolio_heat_guard=heat_guard,
        drawdown_position_scaler=dd_scaler,
    )
    equity_df = engine.run(
        data_slice,
        signal_cache=proba_cache,
        symbol_thresholds=SYMBOL_THRESHOLDS,
    )
    return equity_df, engine.performance_report()


def _slice_by_dates(
    full_data: Dict[str, pd.DataFrame],
    start: Optional[pd.Timestamp],
    end: Optional[pd.Timestamp],
) -> Dict[str, pd.DataFrame]:
    sliced: Dict[str, pd.DataFrame] = {}
    for sym, df in full_data.items():
        sub = df
        if start is not None:
            sub = sub.loc[sub.index >= start]
        if end is not None:
            sub = sub.loc[sub.index <= end]
        if not sub.empty:
            sliced[sym] = sub.copy()
    return sliced


def _print_report(title: str, r: Dict) -> None:
    if "error" in r:
        print(f"\n{title}: {r['error']}\n")
        return
    print("\n" + "=" * 92)
    print(f"  {title}")
    print("=" * 92)
    print(f"  Net Profit (EUR):  {r['total_pnl_net']:>10,.2f}")
    print(f"  Return (%):        {r['return_pct']:>10.2f}")
    print(f"  Max Drawdown (%):  {r['max_drawdown']*100:>10.2f}")
    print(f"  Win Rate (%):      {r['win_rate']*100:>10.2f}")
    print(f"  Trades:            {r['total_trades']:>10}")
    print(f"  Profit Factor:     {r['profit_factor']:>10.3f}")
    print(f"  Sharpe:            {r['sharpe_ratio']:>10.3f}")
    print(f"  Final Equity (EUR):{r['final_equity']:>10,.2f}")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="5-Year Portfolio Simulation")
    parser.add_argument("--v1", action="store_true", help="Use v1 strategy (baseline)")
    args = parser.parse_args()
    use_v2 = not args.v1

    t0 = time.time()
    mode_label = "v2 (SwingStrategyV2 + portfolio risk guards)" if use_v2 else "v1 (baseline)"
    log.info("Strategy mode: %s", mode_label)

    available = set(get_available_symbols())
    symbols = [s for s in EU_SYMBOLS if s in available]
    log.info("Universe: %d symbols", len(symbols))
    if len(symbols) < 5:
        raise RuntimeError(f"Too few symbols found: {symbols}")

    full_data = _prepare_full_data(symbols)
    proba_cache = _score_all(full_data)
    if not proba_cache:
        raise RuntimeError("No models found. Run `python -m t212_miner_bot.run_pipeline` first.")

    train_end_ts  = pd.Timestamp(TRAIN_END,  tz="UTC")
    test_start_ts = pd.Timestamp(TEST_START, tz="UTC")

    full_slice = _slice_by_dates(full_data, None,           None)
    is_slice   = _slice_by_dates(full_data, None,           train_end_ts)
    oos_slice  = _slice_by_dates(full_data, test_start_ts,  None)

    _, full_r = _run_engine(full_slice, proba_cache, INITIAL_CAPITAL, use_v2)
    _print_report(f"FULL 5-YEAR PORTFOLIO [{mode_label}]", full_r)

    _, is_r = _run_engine(is_slice, proba_cache, INITIAL_CAPITAL, use_v2)
    _print_report("FIRST ~4 YEARS (IN-SAMPLE)", is_r)

    _, oos_r = _run_engine(oos_slice, proba_cache, INITIAL_CAPITAL, use_v2)
    _print_report("LAST ~1 YEAR (STRICT OOS – production benchmark)", oos_r)

    # IS/OOS gap check: if OOS return < 50% of IS return, model may be overfit
    is_ret  = is_r.get("return_pct",  0)
    oos_ret = oos_r.get("return_pct", 0)
    if is_ret > 0 and oos_ret < is_ret * 0.5:
        log.warning(
            "OOS return (%.1f%%) is less than 50%% of IS return (%.1f%%)."
            " Consider more regularisation or a different feature set.",
            oos_ret, is_ret,
        )
    elif oos_ret > 0:
        log.info(
            "IS/OOS ratio: %.2f  (OOS %.1f%% vs IS %.1f%%)",
            oos_ret / max(is_ret, 0.001), oos_ret, is_ret,
        )

    log.info("Done in %.1fs", time.time() - t0)


if __name__ == "__main__":
    main()

