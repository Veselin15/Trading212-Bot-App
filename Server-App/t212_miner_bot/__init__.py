"""
t212_miner_bot – AI-driven swing trading bot for Trading212 (EU universe).

Version 4.0 — "BEST_SAFE" production release.
  Live trader runs SwingStrategyV3 (trend-scaled TP + breakout-tight stops) with
  bull-tilt regime sizing, 5 slots, 98% exposure, and a validation-derived
  blocklist.  Backtested OOS: +32.5% / -10.1% DD / Sharpe 1.83 (+9.66% holdout).
  See production.py (single source of truth) and RESEARCH_NOTES.md.

Quick-start
-----------
Train models and run walk-forward backtest:
    python -m t212_miner_bot.run_pipeline

Generate today's live signals (read-only, no orders):
    python -m t212_miner_bot.live_signal

Start live paper-trading loop:
    python -m t212_miner_bot.live_trader --dry-run

Architecture
------------
Core strategy
  strategy.py       SwingStrategy (v1), SwingStrategyV2, SwingStrategyV3 (production)
                    All strategy classes consolidated in one file.

Machine learning
  ensemble_model.py XGBoost + LightGBM weighted-average ensemble (per symbol)
  features.py       59 technical features (trend, momentum, ATR vs median,
                    VWAP distance, volume, multi-timeframe, DTosc, sector RS)
  labeling.py       Triple-barrier labels for supervised training

Backtesting & simulation
  backtest.py           Portfolio engine (signal ranking, position mgmt, exits)
  walk_forward.py       Expanding-window walk-forward retraining

Risk management
  position_sizing.py  ATR-based Kelly-scaled per-trade sizing
  portfolio_risk.py   PortfolioHeatGuard (daily circuit breaker) +
                      DrawdownPositionScaler (0.7× at >3% DD, 0.4× at >7% DD)

Live trading
  live_trader.py      Main loop (5-min poll, 15-min entry gate, state persistence)
  live_signal.py      Read-only signal report
  t212_client.py      Trading212 REST API client
  twelvedata_live.py  TwelveData fallback for live OHLCV

Configuration & data
  config.py           All tunable constants (universe, thresholds, model params)
  production.py       Single source of truth for BEST_SAFE production config
  data_loader.py      OHLCV CSV loading and train/test split
  run_pipeline.py     End-to-end training pipeline
"""

# Lightweight core imports (no heavy ML dependencies at module level)
from t212_miner_bot.strategy import (
    SwingStrategy, SwingStrategyV2, SwingStrategyV3, Signal, Position,
)
from t212_miner_bot.portfolio_risk import PortfolioHeatGuard, DrawdownPositionScaler
from t212_miner_bot.backtest import BacktestEngine
from t212_miner_bot.production import build_engine, build_strategy, PRODUCTION_BLOCKLIST

__version__ = "4.0.0"

# ML imports require sklearn/xgboost/lightgbm/joblib:
#   from t212_miner_bot.ensemble_model import EnsembleModel

__all__ = [
    "SwingStrategy",
    "SwingStrategyV2",
    "SwingStrategyV3",
    "Signal",
    "Position",
    "PortfolioHeatGuard",
    "DrawdownPositionScaler",
    "BacktestEngine",
    "build_engine",
    "build_strategy",
    "PRODUCTION_BLOCKLIST",
]
