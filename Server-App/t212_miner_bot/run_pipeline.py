"""
v4 main pipeline: ensemble model + sector RS features + walk-forward.

    python -m t212_miner_bot.run_pipeline

Steps:
  1. Load OHLCV data for all available EU symbols.
  2. Compute sector relative-strength (cross-asset, done once across all symbols).
  3. Compute per-symbol technical features + attach sector RS.
  4. Generate triple-barrier labels.
  5. Train XGB+LGBM ensemble per symbol (with optional hyperparameter tuning).
  6. Walk-forward backtest – 4 windows with expanding re-train (better OOS estimate).
  7. Print final performance report (v2 strategy + portfolio risk guards).

v4 changes vs v3:
  - Uses SwingStrategyV2 (earlier trail, vol-spike filter, RSI gate)
  - Walk-forward uses 4 windows instead of 2 for more granular OOS validation
  - Portfolio risk guards (daily circuit breaker + drawdown scaler)
  - Tighter model regularisation (see config.XGB_PARAMS / LGBM_PARAMS)
  - Early stopping in ensemble training
"""

from __future__ import annotations

import logging
import sys
import time
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from t212_miner_bot.config import (
    INITIAL_CAPITAL,
    TSCV_N_SPLITS,
    ENABLE_TUNING,
    EU_ONLY_MODE,
    EU_SYMBOLS,
)
from t212_miner_bot.data_loader import (
    get_available_symbols,
    load_multi_timeframe,
    split_train_test,
)
from t212_miner_bot.features import (
    compute_all_features,
    get_feature_columns,
    compute_sector_relative_strength,
    attach_sector_rs,
)
from t212_miner_bot.labeling import apply_triple_barrier_labels, label_balance_report
from t212_miner_bot.ensemble_model import EnsembleModel
from t212_miner_bot.hyperparameter_tuning import tune_xgb_for_symbol
from t212_miner_bot.strategy import SwingStrategyV2
from t212_miner_bot.backtest import BacktestEngine
from t212_miner_bot.portfolio_risk import PortfolioHeatGuard, DrawdownPositionScaler
from t212_miner_bot.walk_forward import walk_forward_backtest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def _prepare_all_symbols(symbols: List[str]) -> Tuple[
    Dict[str, pd.DataFrame],      # full enriched df per symbol
    Dict[str, List[str]],         # feature columns per symbol
]:
    """
    Load, feature-engineer (with sector RS), and label every symbol.
    Returns the full (train+test) dataframes and feature column lists.
    """
    # ── Step A: load all primary data first (needed for sector RS) ───────
    raw_primary: Dict[str, pd.DataFrame] = {}
    raw_secondary: Dict[str, pd.DataFrame | None] = {}
    for sym in symbols:
        try:
            data = load_multi_timeframe(sym)
            raw_primary[sym]   = data["15m"]
            raw_secondary[sym] = data.get("5m")
            log.info("  [%s] loaded %d bars (15 m)", sym, len(data["15m"]))
        except Exception as exc:
            log.error("  [%s] failed to load: %s", sym, exc)

    if not raw_primary:
        return {}, {}

    # ── Step B: compute sector relative-strength (once, cross-asset) ─────
    log.info("Computing sector relative-strength across %d symbols…", len(raw_primary))
    sector_rs = compute_sector_relative_strength(raw_primary)

    # ── Step C: per-symbol feature engineering + labeling ─────────────────
    enriched: Dict[str, pd.DataFrame] = {}
    feature_cols_map: Dict[str, List[str]] = {}

    for sym in raw_primary:
        df = raw_primary[sym]
        df_5m = raw_secondary[sym]

        compute_all_features(df, df_5m, symbol=sym)
        attach_sector_rs(df, sector_rs[sym])
        apply_triple_barrier_labels(df)
        df.dropna(subset=["label"], inplace=True)

        fcols = get_feature_columns(df)
        valid_fcols = [c for c in fcols if not df[c].isna().all()]
        df[valid_fcols] = df[valid_fcols].fillna(0.0)

        enriched[sym] = df
        feature_cols_map[sym] = valid_fcols

        train, test = split_train_test(df)
        log.info(
            "  [%s] train: %d bars (%s → %s)  test: %d bars (%s → %s)",
            sym,
            len(train), train.index[0].date(), train.index[-1].date(),
            len(test),  test.index[0].date(),  test.index[-1].date(),
        )

    return enriched, feature_cols_map


def _train_ensemble(
    symbol: str,
    train: pd.DataFrame,
    feature_cols: List[str],
) -> EnsembleModel:
    """Train one XGB+LGBM ensemble for a symbol."""
    X_train = train[feature_cols]
    y_train = train["label"]

    balance = label_balance_report(train)
    log.info(
        "  [%s] label balance: %d pos / %d neg  (%.1f %% positive)",
        symbol, balance["positives"], balance["negatives"],
        balance["pos_rate"] * 100,
    )

    best_params: dict = {}
    if ENABLE_TUNING and len(X_train) > 1000:
        log.info("  [%s] hyperparameter tuning…", symbol)
        best_params, best_auc = tune_xgb_for_symbol(symbol, X_train, y_train)

    model = EnsembleModel(
        symbol,
        xgb_params=best_params or None,
    )

    if len(X_train) > 500:
        cv_scores = model.time_series_cv(X_train, y_train, n_splits=TSCV_N_SPLITS)
        log.info(
            "  [%s] ensemble CV AUC: %s  (mean %.3f)",
            symbol,
            [round(s, 3) for s in cv_scores],
            np.mean(cv_scores) if cv_scores else 0.0,
        )

    model.train(X_train, y_train)
    model.save()

    imp = model.feature_importance(top_n=8)
    log.info("  [%s] top features:\n%s", symbol, imp.to_string())
    return model


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    t0 = time.time()

    symbols = get_available_symbols()
    if EU_ONLY_MODE:
        symbols = [s for s in symbols if s in EU_SYMBOLS]
        log.info("EU_ONLY_MODE active.")
    log.info("Universe (%d symbols): %s", len(symbols), symbols)

    # ── STEP 1-4: Load and prepare data ───────────────────────────────────
    log.info("=" * 60)
    log.info("STEP 1-4: Data loading, features, labeling")
    log.info("=" * 60)

    all_data, feature_cols_map = _prepare_all_symbols(symbols)
    if not all_data:
        log.error("No data prepared."); sys.exit(1)

    # ── STEP 5: Train ensemble models ─────────────────────────────────────
    log.info("=" * 60)
    log.info("STEP 5: Training XGB+LGBM ensemble models")
    log.info("=" * 60)

    models: Dict[str, EnsembleModel] = {}
    test_sets: Dict[str, pd.DataFrame] = {}

    for sym in all_data:
        fcols = feature_cols_map[sym]
        train, test = split_train_test(all_data[sym])
        if train.empty or test.empty:
            log.warning("  [%s] empty split – skipping", sym); continue

        model = _train_ensemble(sym, train, fcols)
        models[sym] = model
        test_sets[sym] = test

        # Quick test-set evaluation
        X_test = test[fcols].fillna(0.0)
        y_test = test["label"]
        metrics = model.evaluate(X_test, y_test)
        log.info(
            "  [%s] test  accuracy=%.3f  AUC=%.3f  log_loss=%.3f",
            sym, metrics["accuracy"], metrics["roc_auc"], metrics["log_loss"],
        )

    # ── STEP 6: Walk-forward backtest ─────────────────────────────────────
    log.info("=" * 60)
    log.info("STEP 6: Walk-forward backtest (4 windows – more robust OOS estimate)")
    log.info("=" * 60)

    equity_df, window_reports = walk_forward_backtest(
        all_data=all_data,
        feature_cols_map=feature_cols_map,
        n_windows=4,            # was 2 – more windows = finer OOS granularity
        initial_capital=INITIAL_CAPITAL,
    )

    # ── STEP 7: Report ────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("STEP 7: Walk-forward results")
    log.info("=" * 60)

    for wr in window_reports:
        log.info(
            "  Window %d (%s → %s): trades=%d  ret=%.2f%%  sharpe=%.2f  dd=%.2f%%",
            wr["window"], wr["window_start"], wr["window_end"],
            wr.get("total_trades", 0),
            wr.get("return_pct", 0),
            wr.get("sharpe_ratio", 0),
            wr.get("max_drawdown", 0) * 100,
        )

    # Combined across all windows
    all_pnl = sum(w.get("total_pnl_net", 0) for w in window_reports)
    total_trades = sum(w.get("total_trades", 0) for w in window_reports)
    final_equity = window_reports[-1].get("final_equity", INITIAL_CAPITAL) if window_reports else INITIAL_CAPITAL
    combined_ret = (final_equity / INITIAL_CAPITAL - 1) * 100

    log.info("  ─────────────────────────────────────────────────")
    log.info("  Combined: %d trades  net_pnl=%.2f  return=%.2f%%  final_equity=%.2f",
             total_trades, all_pnl, combined_ret, final_equity)

    if not equity_df.empty:
        equity_df.to_csv("t212_miner_bot/wf_equity_curve.csv")
        log.info("Walk-forward equity curve → t212_miner_bot/wf_equity_curve.csv")

    # Also run a single non-WF final report for comparison
    log.info("=" * 60)
    log.info("STEP 7b: Single-shot backtest (v2 strategy + portfolio risk guards)")
    log.info("=" * 60)

    strategy = SwingStrategyV2()
    engine = BacktestEngine(
        strategy=strategy,
        initial_capital=INITIAL_CAPITAL,
        portfolio_heat_guard=PortfolioHeatGuard(),
        drawdown_position_scaler=DrawdownPositionScaler(),
    )
    ss_equity = engine.run(test_sets, models, feature_cols_map)
    ss_report = engine.performance_report()

    for k, v in ss_report.items():
        if k == "report": continue
        log.info("  %-22s %s", k, v)

    log.info("\n--- Per-symbol summary ---")
    sym_summary = engine.per_symbol_summary()
    if not sym_summary.empty:
        log.info("\n%s", sym_summary.to_string())

    trades_df = engine.trades_dataframe()
    if not trades_df.empty:
        trades_df.to_csv("t212_miner_bot/v3_final_trades.csv", index=False)
        log.info("\nTrade log → t212_miner_bot/v3_final_trades.csv")

    if not ss_equity.empty:
        ss_equity.to_csv("t212_miner_bot/v3_equity_curve.csv")
        log.info("Equity curve → t212_miner_bot/v3_equity_curve.csv")

    log.info("\nPipeline finished in %.1f seconds.", time.time() - t0)


if __name__ == "__main__":
    main()
