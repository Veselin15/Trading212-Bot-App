"""
Risk-based position sizing with fractional-share support (Trading212).

Core idea: risk a fixed % of the portfolio on every trade, where the
dollar-risk per share equals the ATR-based stop distance.  This naturally
scales position size with volatility and portfolio equity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from t212_miner_bot.config import (
    RISK_PER_TRADE_PCT,
    MAX_POSITION_PCT,
    MAX_TOTAL_EXPOSURE_PCT,
    MAX_OPEN_POSITIONS,
    SIGNAL_CONFIDENCE_THRESHOLD,
    KELLY_MAX_MULT,
    KELLY_CONFIDENCE_CEIL,
    SYMBOL_MAX_POSITION_PCT,
)


@dataclass
class SizeResult:
    """Output of the position-sizing calculation."""
    shares: float          # fractional shares (e.g. 2.45)
    position_value: float  # shares × entry_price
    risk_amount: float     # dollars at risk = shares × stop_distance
    capped: bool           # True if any limit was applied


def confidence_kelly_multiplier(confidence: float) -> float:
    """
    Scale position size up when the model is highly confident.

    Maps linearly from:
      threshold  → 1.0× (base risk)
      KELLY_CONFIDENCE_CEIL → KELLY_MAX_MULT×

    Clipped so it never exceeds KELLY_MAX_MULT regardless of confidence.
    """
    lo = SIGNAL_CONFIDENCE_THRESHOLD
    hi = KELLY_CONFIDENCE_CEIL
    if confidence <= lo:
        return 1.0
    if confidence >= hi:
        return KELLY_MAX_MULT
    # Linear interpolation
    t = (confidence - lo) / (hi - lo)
    return 1.0 + t * (KELLY_MAX_MULT - 1.0)


def calculate_position_size(
    portfolio_value: float,
    entry_price: float,
    atr: float,
    sl_atr_mult: float,
    risk_pct: float = RISK_PER_TRADE_PCT,
    confidence: float = 0.65,
    symbol: str = "",
    symbol_max_pct_override: Optional[Dict[str, float]] = None,
) -> SizeResult:
    """
    Determine how many (fractional) shares to buy.

    Steps
    -----
    1. Scale risk by model confidence  (Kelly multiplier)
    2. Convert EUR-at-risk → raw share count via ATR stop distance
    3. Cap by the per-symbol position limit (SYMBOL_MAX_POSITION_PCT if the
       symbol is listed, else global MAX_POSITION_PCT)

    For expensive EU stocks the position cap is typically the binding
    constraint; for lower-priced symbols the ATR formula drives sizing.

    Parameters
    ----------
    symbol : optional – used to look up the per-symbol cap; pass it whenever
             the symbol is known (live signal, backtest _open_position, etc.)
    """
    kelly = confidence_kelly_multiplier(confidence)
    risk_amount = portfolio_value * risk_pct * kelly
    stop_distance = atr * sl_atr_mult

    if stop_distance <= 0 or entry_price <= 0:
        return SizeResult(shares=0.0, position_value=0.0, risk_amount=0.0, capped=False)

    raw_shares = risk_amount / stop_distance
    position_value = raw_shares * entry_price

    # Per-symbol cap: use caller-supplied override dict when provided (e.g. risk scaling)
    cap_dict    = symbol_max_pct_override if symbol_max_pct_override is not None else SYMBOL_MAX_POSITION_PCT
    sym_cap_pct = cap_dict.get(symbol, MAX_POSITION_PCT)
    max_value = portfolio_value * sym_cap_pct

    capped = False
    if position_value > max_value:
        raw_shares = max_value / entry_price
        position_value = max_value
        risk_amount = raw_shares * stop_distance
        capped = True

    raw_shares = round(raw_shares, 2)
    position_value = round(raw_shares * entry_price, 2)
    risk_amount = round(raw_shares * stop_distance, 2)

    return SizeResult(
        shares=raw_shares,
        position_value=position_value,
        risk_amount=risk_amount,
        capped=capped,
    )


def check_portfolio_limits(
    portfolio_value: float,
    current_exposure: float,
    num_open_positions: int,
    proposed_value: float,
) -> bool:
    """
    Return True if opening a new position of *proposed_value* would
    still respect global portfolio constraints.
    """
    if num_open_positions >= MAX_OPEN_POSITIONS:
        return False

    new_exposure = current_exposure + proposed_value
    if new_exposure > portfolio_value * MAX_TOTAL_EXPOSURE_PCT:
        return False

    return True


def adjust_for_available_cash(
    cash: float,
    proposed_shares: float,
    entry_price: float,
) -> float:
    """
    If the proposed trade exceeds available cash, reduce share count
    to fit.  Returns the adjusted (possibly smaller) share count.
    """
    cost = proposed_shares * entry_price
    if cost <= cash:
        return proposed_shares
    return round(cash / entry_price, 2) if entry_price > 0 else 0.0
