"""
EU-focused tax and FX cost modelling.

Covers:
  - Dividend withholding tax by jurisdiction
  - FX spread for cross-currency trades (EUR account ↔ USD stocks)
  - Net-return adjustments so backtest/strategy see realistic post-cost PnL
  - Tax-loss harvesting helpers
"""

from __future__ import annotations

from typing import Optional

from t212_miner_bot.config import (
    DIVIDEND_WHT,
    JURISDICTION_MAP,
    FX_SPREAD_PCT,
    EU_SYMBOLS,
    US_SYMBOLS,
    CAPITAL_GAINS_TAX_RATE,
)


def after_tax_annual_profit(
    net_pnl_total: float,
    cgt_rate: float = CAPITAL_GAINS_TAX_RATE,
) -> float:
    """
    Apply capital-gains tax to a year's net realised PnL.

    Annual approximation: within a tax year losses offset gains, so CGT is
    charged only on a positive net total.  A negative net total (a losing
    year) carries forward with no tax due.

    Net PnL here is already after FX costs (the backtest reports it that way),
    so this returns the final in-pocket profit for an EU-resident investor.
    """
    if net_pnl_total <= 0:
        return net_pnl_total
    return net_pnl_total * (1.0 - cgt_rate)


def get_jurisdiction(symbol: str) -> str:
    """
    Derive the tax jurisdiction from the ticker suffix.
    E.g. "ASML.AS" → "NL", "AAPL" → "US".
    """
    for suffix, jurisdiction in JURISDICTION_MAP.items():
        if suffix and symbol.endswith(suffix):
            return jurisdiction
    return "US"  # default: no suffix = US-listed


def dividend_withholding_rate(symbol: str) -> float:
    """Effective dividend withholding tax rate (post-treaty reclaim)."""
    return DIVIDEND_WHT.get(get_jurisdiction(symbol), 0.15)


def estimate_dividend_tax(symbol: str, gross_dividend: float) -> float:
    """Return the withholding tax amount on a gross dividend payment."""
    rate = dividend_withholding_rate(symbol)
    return round(gross_dividend * rate, 4)


def needs_fx_conversion(symbol: str) -> bool:
    """True if trading this symbol from an EUR account involves FX."""
    return symbol in US_SYMBOLS


def fx_cost(trade_value: float, symbol: str) -> float:
    """
    Estimated FX spread cost for a single trade leg.

    Trading212 charges ~0.15% on the FX conversion.
    For EUR-listed stocks traded from an EUR account the cost is zero.
    """
    if not needs_fx_conversion(symbol):
        return 0.0
    return round(trade_value * FX_SPREAD_PCT, 4)


def round_trip_fx_cost(entry_value: float, exit_value: float, symbol: str) -> float:
    """FX cost for opening and closing a position (two legs)."""
    return fx_cost(entry_value, symbol) + fx_cost(exit_value, symbol)


def estimate_tax_drag(
    symbol: str,
    gross_pnl: float,
    trade_value: float,
    gross_dividend: float = 0.0,
) -> float:
    """
    Combined tax + friction drag on a completed trade.

    Includes:
      - FX round-trip cost (entry + exit)
      - Dividend withholding (if any dividend received while holding)

    Capital-gains tax is NOT included here because it depends on the
    investor's country of residence and annual netting.  The backtest
    reports gross and net PnL separately.
    """
    fx = round_trip_fx_cost(trade_value, trade_value + gross_pnl, symbol)
    div_tax = estimate_dividend_tax(symbol, gross_dividend)
    return round(fx + div_tax, 4)


# ── Tax-loss harvesting helpers ───────────────────────────────────────────────

def unrealised_loss(entry_price: float, current_price: float, shares: float) -> float:
    """Return the unrealised loss (positive number) or 0 if in profit."""
    loss = (entry_price - current_price) * shares
    return max(loss, 0.0)


def can_harvest(
    entry_price: float,
    current_price: float,
    shares: float,
    min_loss_eur: float = 50.0,
) -> bool:
    """
    Simple heuristic: flag a position for tax-loss harvesting if the
    unrealised loss exceeds *min_loss_eur*.
    """
    return unrealised_loss(entry_price, current_price, shares) >= min_loss_eur
