"""
Portfolio-level risk management.

Two complementary guards that sit above the per-trade position sizing:

  1. PortfolioHeatGuard  – daily circuit breaker.
     Tracks each day's starting equity and blocks ALL new entries once the
     portfolio falls more than DAILY_DRAWDOWN_LIMIT below that day's open.
     Prevents "digging a bigger hole" on bad days.

  2. DrawdownPositionScaler – drawdown-adaptive sizing.
     Scales down position size as the portfolio's running drawdown deepens.
     This is mathematically equivalent to a partial Kelly reduction: when
     you are already wrong (in drawdown) you bet less, not more.

     Scale tiers (fraction of base position size):
       0 – 3 % drawdown  → 1.00× (full size)
       3 – 7 % drawdown  → 0.70× (reduced)
       > 7 % drawdown    → 0.40× (half size, capital preservation mode)

Neither guard has fitted parameters. The drawdown thresholds (3 %, 7 %)
and the daily circuit-breaker limit (2 %) are conservative first-principles
values, not optimised to historical data.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd


class PortfolioHeatGuard:
    """
    Daily circuit breaker: block new entries when intraday loss exceeds limit.

    Typical use inside BacktestEngine._open_position::

        if not self.heat_guard.can_open(current_equity, current_timestamp):
            return
    """

    def __init__(self, daily_drawdown_limit: float = 0.02):
        """
        Parameters
        ----------
        daily_drawdown_limit : fraction of day-start equity (e.g. 0.02 = 2 %).
            New entries are blocked if equity has fallen this much since the
            start of the trading day.
        """
        self.daily_drawdown_limit = daily_drawdown_limit
        self._day_start_equity: Optional[float] = None
        self._current_day: Optional[int] = None   # trading day (Julian day number)

    def update(self, equity: float, ts: pd.Timestamp) -> None:
        """
        Call once per bar (before entry decisions) to refresh the day reference.
        """
        day = ts.timetuple().tm_yday if hasattr(ts, "timetuple") else 0
        if self._current_day != day:
            self._current_day = day
            self._day_start_equity = equity   # reset reference to today's open equity

    def can_open(self, current_equity: float) -> bool:
        """
        Return True if a new position may be opened.
        Returns False when today's loss already exceeds the daily limit.
        """
        if self._day_start_equity is None or self._day_start_equity <= 0:
            return True
        daily_return = (current_equity - self._day_start_equity) / self._day_start_equity
        return daily_return > -self.daily_drawdown_limit

    def reset(self) -> None:
        self._day_start_equity = None
        self._current_day = None


class DrawdownPositionScaler:
    """
    Scale position sizes down as the portfolio drawdown from its peak deepens.

    Usage inside BacktestEngine._open_position::

        scale = self.dd_scaler.scale_factor(current_equity)
        risk_pct *= scale
    """

    # (drawdown_threshold, size_multiplier) – applied as step-function.
    # Order matters: checked from deepest to shallowest drawdown.
    _TIERS: list[tuple[float, float]] = [
        (0.07, 0.40),   # > 7 % drawdown → 40 % size
        (0.03, 0.70),   # 3–7 % drawdown → 70 % size
        (0.00, 1.00),   # < 3 % drawdown → full size
    ]

    def __init__(self) -> None:
        self._peak_equity: float = 0.0

    def update_peak(self, equity: float) -> None:
        if equity > self._peak_equity:
            self._peak_equity = equity

    def scale_factor(self, current_equity: float) -> float:
        """
        Return the fraction of the base position size to use given the current
        drawdown from the peak equity.
        """
        if self._peak_equity <= 0:
            return 1.0
        drawdown = (self._peak_equity - current_equity) / self._peak_equity
        for threshold, mult in self._TIERS:
            if drawdown >= threshold:
                return mult
        return 1.0

    def current_drawdown_pct(self, current_equity: float) -> float:
        """Current drawdown from peak as a percentage (for logging)."""
        if self._peak_equity <= 0:
            return 0.0
        return max(0.0, (self._peak_equity - current_equity) / self._peak_equity * 100)

    def reset(self) -> None:
        self._peak_equity = 0.0
