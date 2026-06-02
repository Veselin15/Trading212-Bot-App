"""
Production configuration – the optimized "best" strategy for the EU Trading212
portfolio, selected by the two-round optimization (optimize.py / optimize2.py).

Winner: B7_max_profit
  - SwingStrategyV3 with trend-scaled take-profit + breakout-tight stops
  - Bull-tilt sizing: large in a broad uptrend, small in a downtrend
  - Validation-derived blocklist of chronic losers
  - Drawdown throttles OFF for maximum profit (see note below)

Out-of-sample results (1-year OOS, €10k start, 10% CGT):
  - Full year : +33.7 % return, -10.8 % max DD, Sharpe 1.85, after-tax €3,217
  - Holdout   : +10.1 % return (untouched test half) – led every other config

Two presets are exposed:
  build_engine(mode="max_profit")  – the winner exactly (throttles off)
  build_engine(mode="safe")        – identical levers but with the daily
                                     circuit breaker + drawdown scaler ON.
                                     Recommended for LIVE trading: a small
                                     profit give-up buys an automatic brake
                                     against a model break or flash crash.

Re-derive the blocklist periodically (it is fit to the validation window):
    python -m t212_miner_bot.optimize2 --rebuild
"""

from __future__ import annotations

from typing import Optional

from t212_miner_bot.config import (
    INITIAL_CAPITAL, MACRO_BULL_RISK_SCALE, MACRO_BEAR_RISK_SCALE,
    MACRO_REGIME_BULL_THRESHOLD, PYRAMID_ATR_MULT, PYRAMID_FRACTION, PYRAMID_SYMBOLS,
)
from t212_miner_bot.strategy import SwingStrategyV3
from t212_miner_bot.backtest import BacktestEngine
from t212_miner_bot.portfolio_risk import PortfolioHeatGuard, DrawdownPositionScaler

# ── Winning levers (B7) ────────────────────────────────────────────────────
PROD_RISK_SCALE   = MACRO_BULL_RISK_SCALE * 2.0   # 2.80 base
PROD_BULL         = MACRO_BULL_RISK_SCALE * 3.0   # 4.20 in bull regime
PROD_BEAR         = MACRO_BEAR_RISK_SCALE * 1.0   # 0.70 in bear regime
PROD_SLOTS        = 5
PROD_EXPOSURE     = 0.98
PROD_POS_CEILING  = 0.90
PROD_RISK_CEILING = 0.75

# Chronic losers over the validation window (lose >€20 with >=3 trades).
# Re-derive periodically; these are not fixed laws of the market.
PRODUCTION_BLOCKLIST = {"ALV.DE", "SIE.DE", "TTE.PA"}


def build_strategy() -> SwingStrategyV3:
    """The winning strategy: V3 with trend-scaled TP + breakout-tight stops."""
    return SwingStrategyV3(trend_scaled_tp=True, breakout_tight_stop=True)


def build_engine(
    initial_capital: float = INITIAL_CAPITAL,
    mode: str = "safe",
) -> BacktestEngine:
    """
    Build the production backtest/live engine.

    mode="safe"       : throttles on  – RECOMMENDED (default). +32.5% / -10.1% DD
                        on the OOS year; keeps the daily circuit breaker.
    mode="max_profit" : throttles off – the raw optimization winner (B7).
                        +33.7% / -10.8% DD.  Only ~1.2 pp more profit but no
                        automatic brake, so reserved for backtests.
    """
    throttle = (mode == "safe")
    return BacktestEngine(
        strategy=build_strategy(),
        initial_capital=initial_capital,
        pyramid_enabled=True,
        pyramid_atr_mult=PYRAMID_ATR_MULT,
        pyramid_fraction=PYRAMID_FRACTION,
        pyramid_symbols=PYRAMID_SYMBOLS,
        risk_scale=PROD_RISK_SCALE,
        sector_clamping_enabled=True,
        dynamic_macro_risk_enabled=True,
        macro_regime_bull_threshold=MACRO_REGIME_BULL_THRESHOLD,
        macro_bull_risk_scale=PROD_BULL,
        macro_bear_risk_scale=PROD_BEAR,
        max_open_positions=PROD_SLOTS,
        max_total_exposure_pct=PROD_EXPOSURE,
        position_cap_ceiling=PROD_POS_CEILING,
        risk_cap_ceiling=PROD_RISK_CEILING,
        portfolio_heat_guard=PortfolioHeatGuard() if throttle else None,
        drawdown_position_scaler=DrawdownPositionScaler() if throttle else None,
    )
