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

import os
from typing import Optional

from t212_miner_bot.config import (
    INITIAL_CAPITAL, MACRO_BULL_RISK_SCALE, MACRO_BEAR_RISK_SCALE,
    MACRO_REGIME_BULL_THRESHOLD, PYRAMID_ATR_MULT, PYRAMID_FRACTION, PYRAMID_SYMBOLS,
)
from t212_miner_bot.strategy import SwingStrategyV3
from t212_miner_bot.backtest import BacktestEngine
from t212_miner_bot.portfolio_risk import PortfolioHeatGuard, DrawdownPositionScaler


def _env_float(name: str, default: float) -> float:
    """Read a float from the environment, falling back to *default* on unset/garbage."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


# ── Winning levers (B7) ────────────────────────────────────────────────────
PROD_RISK_SCALE   = MACRO_BULL_RISK_SCALE * 2.0   # 2.80 base
# Bull-regime risk multiplier.  Was 4.20 (=1.4*3).  Owner's max-profit choice:
# 6.0 — the exact top row of the sweep (cap0.90 x6 bull6 = ~28.6% OOS / -11.3%
# DD / Sharpe 1.66).  Note this SATURATES: bull 6, 8, 10 gave identical results
# because the book is already ~fully invested (exposure 0.98), so >6 adds nothing.
# Env-overridable (e.g. PROD_BULL=4.2 to soften single-name sizing).
PROD_BULL         = _env_float("PROD_BULL", 6.0)
PROD_BEAR         = MACRO_BEAR_RISK_SCALE * 1.0   # 0.70 in bear regime
PROD_SLOTS        = 6     # 6 (was 5): +1 name of diversification, tested marginally best
PROD_EXPOSURE     = 0.98

# Per-position and per-trade-risk ceilings.  PROD_POS_CEILING is the hard cap on
# how much of the portfolio one position may consume after the bull/bear risk
# multiplier.
#
# Default 0.90 — OWNER'S EXPLICIT CHOICE: maximise profit subject to Max DD <= 15%.
# The max-profit sweep (sim_portfolio_mgmt.py, OOS year, live-faithful throttle-
# off engine = how live_trader actually runs) found cap0.90 x6 is the highest
# return config inside the 15% DD budget: ~28.6% return, -11.3% DD, Sharpe 1.66.
# ~28% is the practical ceiling — a cash account has no leverage, so the book is
# already ~fully invested (exposure 0.98); raising bull beyond ~6 or widening the
# book does NOT add return, and lower caps simply leave cash idle.
#
# TRADE-OFF THE OWNER ACCEPTED: cap0.90 allows ~90% of the account in ONE stock
# (avg ~46%).  The -11.3% backtest DD does NOT capture single-stock gap risk — a
# 20-30% overnight drop in a 90%-weighted name is a ~18-27% account hit, past the
# 15% budget.  Lower the cap to reduce that tail (0.25 ≈ max ~38% per name and
# -4.4% DD; 0.20 is the risk-adjusted optimum, Sharpe 1.50).  Env-overridable:
#     PROD_POS_CEILING=0.25   PROD_RISK_CEILING=0.75
PROD_POS_CEILING  = _env_float("PROD_POS_CEILING", 0.90)
PROD_RISK_CEILING = _env_float("PROD_RISK_CEILING", 0.75)

# Chronic losers over the validation window (lose >€20 with >=3 trades).
# Re-derive periodically; these are not fixed laws of the market.
PRODUCTION_BLOCKLIST = {"ALV.DE", "SIE.DE", "TTE.PA"}


def build_strategy() -> SwingStrategyV3:
    """v5 "let winners run" strategy: V3 with WIDE trend-scaled take-profit.

    The key change vs the old config: take-profit widened from 5/6/7 ATR to
    10/15/20 ATR so winning trades ride the trend extension instead of being
    capped early (the ML flags the setup; we give it room).  Entry gate slightly
    loosened (ADX 15→12, cooldown 8→6).  Loss side (SL/trail) unchanged — that
    is why the edge is robust.

    Validated on the OOS year: return 28.6%→58.7%, Max DD -11.3%→-8.0%,
    Sharpe 1.66→2.77, profit factor 1.29→1.61.  Full 5y incl. the 2022 bear:
    Max DD -13.0%→-10.6%, PF 2.19→2.56.  See AI-Trading/new_trading212bot_v5/
    V5_NOTES.md for the full sweep + caveats.  Revert by restoring the v4 values
    (tp_atr_mult=5, tp_strong_adx=6, tp_very_strong_adx=7, min_adx=15, cooldown_bars=8).
    """
    return SwingStrategyV3(
        trend_scaled_tp=True,
        breakout_tight_stop=True,
        tp_atr_mult=10.0,         # standard-trend TP (was 5.0)
        tp_strong_adx=15.0,       # ADX>=25 TP (was 6.0)
        tp_very_strong_adx=20.0,  # ADX>=35 TP (was 7.0)
        min_adx=12.0,             # entry gate (was 15)
        cooldown_bars=6,          # re-entry cooldown (was 8)
    )


def build_engine(
    initial_capital: float = INITIAL_CAPITAL,
    mode: str = "safe",
    position_cap_ceiling: float = PROD_POS_CEILING,
    risk_cap_ceiling: float = PROD_RISK_CEILING,
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
        position_cap_ceiling=position_cap_ceiling,
        risk_cap_ceiling=risk_cap_ceiling,
        portfolio_heat_guard=PortfolioHeatGuard() if throttle else None,
        drawdown_position_scaler=DrawdownPositionScaler() if throttle else None,
    )
