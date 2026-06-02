"""
Fractional Kelly Criterion sizing  (idea #3)
=============================================

The static SYMBOL_RISK_PCT tiers ("Tier S = 15%, Tier A = 12%, ...") were hand-
assigned.  The Kelly criterion replaces that judgement with mathematics:
allocate capital in proportion to each setup's *empirical* edge so the portfolio
maximises long-run compound growth.

For a setup with win probability W and win/loss ratio R = (avg win / avg loss):

    f* = W - (1 - W) / R        (full Kelly fraction of bankroll to risk)

Full Kelly is too aggressive (it maximises growth but with violent drawdowns),
so we use FRACTIONAL Kelly (default 0.5 x f*), which keeps ~75% of the growth
at ~50% of the variance — the standard professional compromise.

Calibration is done on the TRAINING period only: we run a probe backtest to get
each symbol's realised W and R, compute fractional Kelly, and clip to a sane
band.  The result is a {symbol: risk_pct} dict fed to BacktestEngine via
`symbol_risk_override`.  No OOS data is used.

Symbols with too few trades or a non-positive Kelly edge fall back to a
conservative floor (they simply get sized small rather than excluded).
"""

from __future__ import annotations

import logging
from typing import Dict

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def kelly_fraction(win_rate: float, win_loss_ratio: float) -> float:
    """Full Kelly fraction f* = W - (1-W)/R.  Returns 0 if edge is non-positive."""
    if win_loss_ratio <= 0:
        return 0.0
    f = win_rate - (1.0 - win_rate) / win_loss_ratio
    return max(f, 0.0)


def calibrate_from_trades(
    trades: pd.DataFrame,
    fraction: float = 0.5,
    min_trades: int = 8,
    risk_floor: float = 0.03,
    risk_cap: float = 0.30,
    default_risk: float = 0.08,
) -> Dict[str, float]:
    """
    Compute a {symbol: risk_pct} map from a probe backtest's trade log.

    Parameters
    ----------
    trades       : DataFrame with columns symbol, pnl_net (one row per trade).
    fraction     : Kelly fraction (0.5 = half-Kelly).
    min_trades   : symbols with fewer trades use `default_risk` (insufficient data).
    risk_floor   : minimum risk % for any traded symbol (never zero — let the
                   model decide entries; Kelly only sizes them).
    risk_cap     : maximum risk % per symbol (hard safety cap).
    default_risk : fallback when a symbol has too few trades to calibrate.
    """
    if trades is None or trades.empty:
        return {}

    out: Dict[str, float] = {}
    for sym, grp in trades.groupby("symbol"):
        pnl = grp["pnl_net"].values
        n = len(pnl)
        if n < min_trades:
            out[sym] = default_risk
            continue
        wins = pnl[pnl > 0]
        losses = pnl[pnl <= 0]
        W = len(wins) / n
        avg_win = wins.mean() if len(wins) else 0.0
        avg_loss = abs(losses.mean()) if len(losses) else 0.0
        R = (avg_win / avg_loss) if avg_loss > 0 else (2.0 if avg_win > 0 else 0.0)

        f = kelly_fraction(W, R) * fraction
        out[sym] = float(np.clip(f, risk_floor, risk_cap))

    logger.info("Kelly risk weights (%d symbols): %s", len(out),
                {k: round(v, 3) for k, v in sorted(out.items(), key=lambda x: -x[1])[:8]})
    return out
