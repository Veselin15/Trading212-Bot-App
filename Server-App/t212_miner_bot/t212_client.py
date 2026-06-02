"""
Trading 212 REST API Client  –  Paper-trading edition
======================================================

Provides a thin, synchronous wrapper around the T212 equity API.
All credentials and the target environment (demo vs live) are read
from environment variables so nothing secret is ever hard-coded.

Environment variables
---------------------
  T212_API_KEY       Required.  Your T212 API token.
  T212_BASE_URL      Optional.  Default: https://demo.trading212.com
                     Set to https://live.trading212.com for real money.

Rate limits (T212 enforces these)
----------------------------------
  Orders             1 / 1 s  (we add a 1.2 s guard)
  Portfolio / Cash   1 / 1 s  (we add a 1.0 s guard)
  Instruments list   no formal limit; fetched once at startup
  Generic            1 / 1 s

Usage
-----
    from t212_miner_bot.t212_client import T212Client
    client = T212Client()
    cash = client.get_cash()
    client.place_market_order("ASMLa_EQ", quantity=2)   # buy 2 shares
    client.place_market_order("ASMLa_EQ", quantity=-2)  # sell 2 shares
"""

from __future__ import annotations

import logging
import os
import time
import base64
from typing import Dict, List, Optional

import requests

log = logging.getLogger(__name__)

_DEFAULT_BASE = "https://demo.trading212.com"
_ORDER_GUARD  = 1.2   # minimum seconds between order calls
_DATA_GUARD   = 1.1   # minimum seconds between data calls (T212 often enforces 1/s)


class T212Client:
    """Synchronous wrapper for the Trading 212 equity API."""

    def __init__(self) -> None:
        self.api_key  = os.getenv("T212_API_KEY", "").strip()
        self.secret_key = os.getenv("T212_SECRET_KEY", "").strip()
        raw_url = os.getenv("T212_BASE_URL", _DEFAULT_BASE).rstrip("/")
        # Strip trailing /api/v0 if the user included it in their env var;
        # the client appends the full path itself.
        if raw_url.endswith("/api/v0"):
            raw_url = raw_url[: -len("/api/v0")]
        self.base_url = raw_url
        self._session = requests.Session()

        if not self.api_key:
            log.warning(
                "T212_API_KEY is not set.  All API calls will fail with 401.  "
                "Set the env var before starting the live trader."
            )

        # Simple time-based rate guard (wall-clock, not token bucket)
        self._last_order_call: float = 0.0
        self._last_data_call:  float = 0.0

    # ── Internal helpers ──────────────────────────────────────────────────

    @property
    def _headers(self) -> Dict[str, str]:
        if self.secret_key:
            token = base64.b64encode(f"{self.api_key}:{self.secret_key}".encode("utf-8")).decode("utf-8")
            auth = f"Basic {token}"
        else:
            auth = f"Bearer {self.api_key}"
        return {
            "Authorization": auth,
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }

    def _get(self, path: str, params: Optional[dict] = None) -> dict | list:
        self._guard_data()
        url = f"{self.base_url}{path}"
        for attempt in range(3):
            try:
                r = self._session.get(url, headers=self._headers, params=params, timeout=15)
                if r.status_code == 429:
                    retry_after = float(r.headers.get("Retry-After", 1))
                    log.warning("Rate-limited on GET %s, sleeping %ds", path, retry_after)
                    time.sleep(max(1.1, retry_after))
                    continue
                if r.status_code == 401:
                    # Fail fast for bad credentials (no retries help here).
                    raise PermissionError(
                        "Trading212 API returned 401 Unauthorized. "
                        "Check T212_API_KEY (and T212_SECRET_KEY if required) in your .env."
                    )
                if r.status_code >= 400:
                    raise RuntimeError(f"GET {path} failed ({r.status_code}): {r.text}")
                r.raise_for_status()
                return r.json()
            except requests.RequestException as exc:
                # Surface DNS/network issues clearly (common on Windows: Errno 11001 getaddrinfo failed)
                s = str(exc)
                if ("NameResolutionError" in s) or ("getaddrinfo failed" in s) or ("Failed to resolve" in s):
                    raise RuntimeError(
                        "Network/DNS error while calling Trading212. "
                        "Your machine could not resolve the Trading212 host name. "
                        "This is not a bot logic error; check your DNS/VPN/firewall/connection."
                    ) from exc
                log.warning("GET %s attempt %d failed: %s", path, attempt + 1, exc)
                if attempt < 2:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"GET {path} failed after 3 attempts")

    def _post(self, path: str, body: dict) -> dict:
        self._guard_order()
        url = f"{self.base_url}{path}"
        for attempt in range(4):
            try:
                r = self._session.post(url, headers=self._headers, json=body, timeout=15)
                if r.status_code == 429:
                    retry_after = float(r.headers.get("Retry-After", 1))
                    log.warning("Rate-limited on POST %s, sleeping %ds", path, retry_after)
                    time.sleep(max(1.1, retry_after))
                    continue
                if r.status_code == 401:
                    raise PermissionError(
                        "Trading212 API returned 401 Unauthorized. "
                        "Check T212_API_KEY (and T212_SECRET_KEY if required) in your .env."
                    )
                if r.status_code >= 400:
                    raise RuntimeError(f"POST {path} failed ({r.status_code}): {r.text}")
                r.raise_for_status()
                return r.json()
            except requests.RequestException as exc:
                s = str(exc)
                if ("NameResolutionError" in s) or ("getaddrinfo failed" in s) or ("Failed to resolve" in s):
                    raise RuntimeError(
                        "Network/DNS error while placing Trading212 order. "
                        "Your machine could not resolve the Trading212 host name. "
                        "Check your DNS/VPN/firewall/connection."
                    ) from exc
                log.warning("POST %s attempt %d failed: %s", path, attempt + 1, exc)
                if attempt < 3:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"POST {path} failed after 4 attempts")

    def _delete(self, path: str) -> None:
        self._guard_order()
        url = f"{self.base_url}{path}"
        for attempt in range(3):
            try:
                r = self._session.delete(url, headers=self._headers, timeout=15)
                if r.status_code == 404:
                    log.debug("DELETE %s → 404 (already gone)", path)
                    return
                if r.status_code == 429:
                    retry_after = int(r.headers.get("Retry-After", 5))
                    time.sleep(retry_after)
                    continue
                r.raise_for_status()
                return
            except requests.RequestException as exc:
                log.warning("DELETE %s attempt %d failed: %s", path, attempt + 1, exc)
                if attempt < 2:
                    time.sleep(2 ** attempt)

    def _guard_order(self) -> None:
        elapsed = time.monotonic() - self._last_order_call
        if elapsed < _ORDER_GUARD:
            time.sleep(_ORDER_GUARD - elapsed)
        self._last_order_call = time.monotonic()

    def _guard_data(self) -> None:
        elapsed = time.monotonic() - self._last_data_call
        if elapsed < _DATA_GUARD:
            time.sleep(_DATA_GUARD - elapsed)
        self._last_data_call = time.monotonic()

    # ── Account & Portfolio ───────────────────────────────────────────────

    def get_account_info(self) -> dict:
        """Return {currencyCode, id} from the account endpoint."""
        return self._get("/api/v0/equity/account/info")

    def get_cash(self) -> dict:
        """Return {free, invested, result, total, ppl, blocked} (all in EUR)."""
        return self._get("/api/v0/equity/account/cash")

    def get_portfolio(self) -> list:
        """Return list of open positions with avgPrice and currentQuantity."""
        return self._get("/api/v0/equity/portfolio")

    def get_positions(self) -> list:
        """Return enriched positions including currentPrice and ppl."""
        return self._get("/api/v0/equity/positions")

    def get_orders(self) -> list:
        """Return all currently pending orders."""
        return self._get("/api/v0/equity/orders")

    # ── Instruments / Ticker resolution ───────────────────────────────────

    def get_instruments(self) -> list:
        """
        Fetch the full instrument metadata list from T212.
        Each entry: {ticker, name, shortName, isin, currencyCode, type, …}
        Used once at startup to build the yfinance→T212 ticker mapping.
        """
        return self._get("/api/v0/equity/metadata/instruments")

    # ── Order placement ───────────────────────────────────────────────────

    def place_market_order(
        self,
        ticker: str,
        quantity: float,
    ) -> dict:
        """
        Place a market order.

        Parameters
        ----------
        ticker   : T212 instrument ticker  (e.g. "ASMLa_EQ")
        quantity : positive = buy, negative = sell
        """
        body = {"ticker": ticker, "quantity": quantity}
        log.info("  MARKET ORDER  %s  qty=%+.4f", ticker, quantity)
        return self._post("/api/v0/equity/orders/market", body)

    def place_stop_order(
        self,
        ticker: str,
        quantity: float,
        stop_price: float,
    ) -> dict:
        """
        Place a stop order (used for protective stop-losses at the broker).

        Parameters
        ----------
        ticker     : T212 instrument ticker
        quantity   : positive = buy-stop, negative = sell-stop (stop-loss)
        stop_price : price that triggers the order
        """
        body = {
            "ticker":       ticker,
            "quantity":     quantity,
            "stopPrice":    round(stop_price, 4),
            "timeValidity": "GOOD_TILL_CANCEL",
        }
        log.info("  STOP ORDER  %s  qty=%+.4f  @%.4f", ticker, quantity, stop_price)
        return self._post("/api/v0/equity/orders/stop", body)

    def cancel_order(self, order_id: str | int) -> None:
        """Cancel a pending order by its T212 order ID."""
        log.info("  CANCEL ORDER  %s", order_id)
        self._delete(f"/api/v0/equity/orders/{order_id}")

    # ── Context manager ───────────────────────────────────────────────────

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self._session.close()

    def close(self):
        self._session.close()
