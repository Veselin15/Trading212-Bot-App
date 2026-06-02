"""
Walk-forward training and evaluation.

The test period is divided into a configurable number of windows.
At the start of each window we retrain the ensemble on ALL data up to
that point (expanding window), then run the backtest on the window.
This prevents the model from going stale as market regimes change.

Diagram:

  |────── TRAIN ──────|── TEST window 1 ──|── TEST window 2 ──|
                       ↑ retrain here       ↑ retrain here

Usage::

    results = walk_forward_backtest(
        all_data=all_data,   # {symbol: df with features & labels}
        n_windows=2,
    )
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from t212_miner_bot.config import (
    TRAIN_END,
    TEST_START,
    INITIAL_CAPITAL,
    SL_ATR_MULT,
)
from t212_miner_bot.ensemble_model import EnsembleModel
from t212_miner_bot.strategy import SwingStrategy
from t212_miner_bot.backtest import BacktestEngine

logger = logging.getLogger(__name__)


def _build_windows(
    test_start: datetime,
    test_end: datetime,
    n_windows: int,
) -> List[Tuple[datetime, datetime]]:
    """Split the test period into *n_windows* equal-length windows."""
    total_days = (test_end - test_start).days
    window_days = total_days // n_windows
    windows: List[Tuple[datetime, datetime]] = []
    for i in range(n_windows):
        w_start = test_start + timedelta(days=i * window_days)
        w_end = (
            test_start + timedelta(days=(i + 1) * window_days - 1)
            if i < n_windows - 1
            else test_end
        )
        windows.append((w_start, w_end))
    return windows


def walk_forward_backtest(
    all_data: Dict[str, pd.DataFrame],
    feature_cols_map: Dict[str, List[str]],
    n_windows: int = 2,
    initial_capital: float = INITIAL_CAPITAL,
) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    Run a walk-forward backtest.

    For each window:
      1. Retrain an EnsembleModel for each symbol on expanding training set.
      2. Run BacktestEngine on the window's test slice.
      3. Carry the ending equity forward as starting capital for the next window.

    Returns:
      - equity_df : combined equity curve across all windows
      - window_reports : list of per-window performance dictionaries
    """
    # Determine overall test end from data
    test_end_ts = max(df.index[-1] for df in all_data.values())
    test_end = test_end_ts.to_pydatetime().replace(tzinfo=None)

    windows = _build_windows(TEST_START, test_end, n_windows)
    logger.info("Walk-forward windows:")
    for i, (ws, we) in enumerate(windows):
        logger.info("  Window %d: %s → %s", i + 1, ws.date(), we.date())

    equity_curves: List[pd.DataFrame] = []
    window_reports: List[Dict] = []
    capital = initial_capital

    for w_idx, (w_start, w_end) in enumerate(windows):
        logger.info("=" * 55)
        logger.info("WALK-FORWARD  window %d / %d", w_idx + 1, n_windows)
        logger.info("=" * 55)

        w_start_ts = pd.Timestamp(w_start, tz="UTC")
        w_end_ts   = pd.Timestamp(w_end,   tz="UTC")
        train_end_ts = pd.Timestamp(TRAIN_END, tz="UTC")

        # ── Retrain on expanding window ────────────────────────────────
        models: Dict[str, EnsembleModel] = {}
        for symbol, df in all_data.items():
            fcols = feature_cols_map.get(symbol, [])
            if not fcols:
                continue

            # Training data: everything before this window's start
            train_cutoff = w_start_ts - pd.Timedelta(seconds=1)
            train_df = df.loc[:train_cutoff].dropna(subset=["label"])

            if len(train_df) < 500:
                logger.warning("  [%s] not enough training data (%d rows), skipping", symbol, len(train_df))
                continue

            X_tr = train_df[fcols].fillna(0.0)
            y_tr = train_df["label"]

            logger.info("  [%s] retraining on %d bars (up to %s)", symbol, len(X_tr), train_cutoff.date())
            model = EnsembleModel(symbol)
            model.train(X_tr, y_tr)
            models[symbol] = model

        if not models:
            logger.warning("  No models trained for window %d – skipping", w_idx + 1)
            continue

        # ── Slice test window ──────────────────────────────────────────
        window_test: Dict[str, pd.DataFrame] = {}
        for symbol, df in all_data.items():
            if symbol not in models:
                continue
            slice_df = df.loc[w_start_ts:w_end_ts].copy()
            if not slice_df.empty:
                window_test[symbol] = slice_df

        if not window_test:
            continue

        # ── Run backtest on window ─────────────────────────────────────
        strategy = SwingStrategy()
        engine = BacktestEngine(strategy=strategy, initial_capital=capital)
        eq_df = engine.run(window_test, models, feature_cols_map)

        report = engine.performance_report()
        report["window"] = w_idx + 1
        report["window_start"] = str(w_start.date())
        report["window_end"] = str(w_end.date())
        window_reports.append(report)

        logger.info(
            "  Window %d result: trades=%d  return=%.2f%%  sharpe=%.2f  max_dd=%.2f%%",
            w_idx + 1,
            report.get("total_trades", 0),
            report.get("return_pct", 0),
            report.get("sharpe_ratio", 0),
            report.get("max_drawdown", 0) * 100,
        )

        if not eq_df.empty:
            equity_curves.append(eq_df)

        # Carry final equity into next window
        final_eq = report.get("final_equity", capital)
        capital = final_eq

    combined = pd.concat(equity_curves) if equity_curves else pd.DataFrame()
    return combined, window_reports
