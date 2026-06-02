"""
Trading212 API execution layer – **placeholder implementation**.

All functions simulate the expected Trading212 REST API surface.  Replace
the bodies with real HTTP calls once the API key / endpoint is available.

Trading212 Invest/ISA API endpoints (when available):
  - POST /api/v0/equity/orders         → place order
  - DELETE /api/v0/equity/orders/{id}   → cancel order
  - GET  /api/v0/equity/portfolio       → open positions
  - GET  /api/v0/equity/account/cash    → account cash
  - GET  /api/v0/equity/orders          → pending orders
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class OrderResult:
    order_id: str
    symbol: str
    side: str           # "BUY" or "SELL"
    shares: float
    price: float        # fill price (or limit price for pending)
    status: str         # "FILLED", "PENDING", "REJECTED"
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PortfolioPosition:
    symbol: str
    shares: float
    avg_price: float
    current_price: float
    pnl: float


class Trading212Client:
    """
    Placeholder client for the Trading212 Invest/ISA API.

    Every method logs the action and returns a synthetic response so the
    rest of the bot can be developed and backtested without a live connection.
    """

    def __init__(self, api_key: str = "", base_url: str = ""):
        self.api_key = api_key
        self.base_url = base_url or "https://live.trading212.com"
        self._simulated_positions: Dict[str, PortfolioPosition] = {}
        self._next_order_id = 1

    # ── Orders ────────────────────────────────────────────────────────────

    def place_buy_order(
        self,
        symbol: str,
        shares: float,
        limit_price: Optional[float] = None,
    ) -> OrderResult:
        """
        Place a fractional BUY order.

        TODO: Replace with actual POST /api/v0/equity/orders
        """
        oid = f"SIM-{self._next_order_id:06d}"
        self._next_order_id += 1
        price = limit_price or 0.0

        logger.info(
            "[PLACEHOLDER] BUY %.2f shares of %s @ %.4f  (order %s)",
            shares, symbol, price, oid,
        )

        return OrderResult(
            order_id=oid,
            symbol=symbol,
            side="BUY",
            shares=shares,
            price=price,
            status="FILLED",
        )

    def place_sell_order(
        self,
        symbol: str,
        shares: float,
        limit_price: Optional[float] = None,
    ) -> OrderResult:
        """
        Place a fractional SELL order (close long position).

        TODO: Replace with actual POST /api/v0/equity/orders
        """
        oid = f"SIM-{self._next_order_id:06d}"
        self._next_order_id += 1
        price = limit_price or 0.0

        logger.info(
            "[PLACEHOLDER] SELL %.2f shares of %s @ %.4f  (order %s)",
            shares, symbol, price, oid,
        )

        return OrderResult(
            order_id=oid,
            symbol=symbol,
            side="SELL",
            shares=shares,
            price=price,
            status="FILLED",
        )

    # ── Portfolio queries ─────────────────────────────────────────────────

    def get_positions(self) -> List[PortfolioPosition]:
        """
        Fetch all open positions.

        TODO: Replace with GET /api/v0/equity/portfolio
        """
        logger.info("[PLACEHOLDER] Fetching portfolio positions")
        return list(self._simulated_positions.values())

    def get_account_cash(self) -> float:
        """
        Return available cash balance (EUR).

        TODO: Replace with GET /api/v0/equity/account/cash
        """
        logger.info("[PLACEHOLDER] Fetching account cash")
        return 0.0

    # ── Order management ──────────────────────────────────────────────────

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel a pending order.

        TODO: Replace with DELETE /api/v0/equity/orders/{id}
        """
        logger.info("[PLACEHOLDER] Cancelling order %s", order_id)
        return True

    def get_pending_orders(self) -> List[OrderResult]:
        """
        List all pending (unfilled) orders.

        TODO: Replace with GET /api/v0/equity/orders
        """
        logger.info("[PLACEHOLDER] Fetching pending orders")
        return []

    # ── Account info ──────────────────────────────────────────────────────

    def get_account_info(self) -> Dict:
        """
        Fetch account metadata (currency, type, etc.).

        TODO: Replace with GET /api/v0/equity/account/info
        """
        logger.info("[PLACEHOLDER] Fetching account info")
        return {
            "currency": "EUR",
            "account_type": "INVEST",
        }
