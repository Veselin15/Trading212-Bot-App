from __future__ import annotations

import asyncio
import base64
import math
import re
import time
from dataclasses import dataclass
from typing import Any

import aiohttp

from .config import SYMBOLS_MAP, T212_API_KEY, T212_BASE_URL, T212_SECRET_KEY


class T212APIError(RuntimeError):
    pass


@dataclass
class AsyncTokenBucket:
    capacity: int
    refill_rate_per_sec: float

    def __post_init__(self) -> None:
        self._tokens = float(self.capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> None:
        async with self._lock:
            while True:
                self._refill()
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return

                missing = tokens - self._tokens
                wait_time = missing / self.refill_rate_per_sec
                await asyncio.sleep(max(wait_time, 0.01))

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._last_refill = now
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate_per_sec)


class AsyncT212Client:
    def __init__(
        self,
        api_key: str = T212_API_KEY,
        secret_key: str = T212_SECRET_KEY,
        base_url: str = T212_BASE_URL,
        timeout_seconds: int = 20,
    ) -> None:
        if not api_key:
            raise EnvironmentError("Missing T212_API_KEY environment variable.")
        self.api_key = api_key
        self.secret_key = secret_key
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self.session: aiohttp.ClientSession | None = None
        self.max_rate_limit_retries = 3

        # 50 requests/minute for order endpoints.
        self.order_limiter = AsyncTokenBucket(capacity=50, refill_rate_per_sec=50.0 / 60.0)
        # 1 request/second for portfolio and data endpoints.
        self.data_limiter = AsyncTokenBucket(capacity=1, refill_rate_per_sec=1.0)
        # GET /equity/orders is limited to 1 request / 5s (docs).
        self.orders_list_limiter = AsyncTokenBucket(capacity=1, refill_rate_per_sec=1.0 / 5.2)
        self._resolved_ticker_cache: dict[str, str] = {}
        self._instrument_ticker_index: dict[str, str] | None = None
        self._ticker_resolve_lock = asyncio.Lock()

    def _map_ticker(self, ticker: str) -> str:
        # Accept both yfinance symbols and already-mapped Trading 212 tickers.
        if ticker in SYMBOLS_MAP:
            return SYMBOLS_MAP[ticker]
        if ticker in SYMBOLS_MAP.values():
            return ticker
        return ticker

    @staticmethod
    def _ticker_key(ticker: str) -> str:
        return str(ticker).strip().upper()

    async def _load_instrument_ticker_index(self) -> dict[str, str]:
        """
        Load and cache Trading 212 instrument metadata tickers keyed by uppercase ticker.
        """
        if self._instrument_ticker_index is not None:
            return self._instrument_ticker_index

        async with self._ticker_resolve_lock:
            if self._instrument_ticker_index is not None:
                return self._instrument_ticker_index

            instruments = await self._request(
                "GET",
                "/api/v0/equity/metadata/instruments",
                order_call=False,
            )
            if not isinstance(instruments, list):
                raise T212APIError(
                    "Unexpected metadata format from /api/v0/equity/metadata/instruments."
                )

            ticker_by_upper: dict[str, str] = {}
            for row in instruments:
                if not isinstance(row, dict):
                    continue
                raw_ticker = str(row.get("ticker", "")).strip()
                if not raw_ticker:
                    continue
                ticker_by_upper[self._ticker_key(raw_ticker)] = raw_ticker

            if not ticker_by_upper:
                raise T212APIError(
                    "No tradable equity instruments returned by /api/v0/equity/metadata/instruments."
                )

            self._instrument_ticker_index = ticker_by_upper
            return self._instrument_ticker_index

    @staticmethod
    def _extract_symbol_root(raw_ticker: str) -> str:
        upper = str(raw_ticker).strip().upper()
        if not upper:
            return ""
        for sep in ("_", "."):
            if sep in upper:
                return upper.split(sep, 1)[0]
        return upper

    async def _resolve_ticker(self, ticker: str) -> str:
        """
        Resolve user/input symbols (e.g. AAPL) to a tradable Trading 212 ticker
        (e.g. AAPL_US_EQ). This avoids live order failures with "Ticker does not exist".
        """
        mapped = self._map_ticker(ticker)
        mapped_key = self._ticker_key(mapped)
        input_key = self._ticker_key(ticker)

        if mapped_key in self._resolved_ticker_cache:
            return self._resolved_ticker_cache[mapped_key]
        if input_key in self._resolved_ticker_cache:
            return self._resolved_ticker_cache[input_key]

        ticker_by_upper = await self._load_instrument_ticker_index()
        ticker_pool = list(ticker_by_upper.values())

        # 1) Prefer exact mapped ticker match (case-insensitive).
        direct_match = ticker_by_upper.get(mapped_key)
        if direct_match:
            self._resolved_ticker_cache[mapped_key] = direct_match
            self._resolved_ticker_cache[input_key] = direct_match
            return direct_match

        # 2) If caller passed a tradable ticker directly, accept it.
        direct_input_match = ticker_by_upper.get(input_key)
        if direct_input_match:
            self._resolved_ticker_cache[mapped_key] = direct_input_match
            self._resolved_ticker_cache[input_key] = direct_input_match
            return direct_input_match

        # 3) If caller uses Yahoo-style symbol ROOT.EX (e.g. SHEL.AS), try ROOT{ex_first_letter}_EQ.
        if "." in input_key:
            root, market = input_key.split(".", 1)
            market = market.strip()
            if root and market:
                exchange_style_candidate = f"{root}{market[0]}_EQ"
                exchange_style_match = ticker_by_upper.get(exchange_style_candidate)
                if exchange_style_match:
                    self._resolved_ticker_cache[mapped_key] = exchange_style_match
                    self._resolved_ticker_cache[input_key] = exchange_style_match
                    return exchange_style_match

        # 4) Fall back to root-based inference.
        candidate_roots = [
            self._extract_symbol_root(mapped),
            self._extract_symbol_root(ticker),
        ]
        seen_roots: set[str] = set()
        normalized_roots: list[str] = []
        for root in candidate_roots:
            if root and root not in seen_roots:
                normalized_roots.append(root)
                seen_roots.add(root)

        for root in normalized_roots:
            preferred_candidates = (
                f"{root}_US_EQ",
                f"{root}_EQ",
                root,
            )
            for candidate in preferred_candidates:
                resolved = ticker_by_upper.get(candidate)
                if resolved:
                    self._resolved_ticker_cache[mapped_key] = resolved
                    self._resolved_ticker_cache[input_key] = resolved
                    return resolved

        for root in normalized_roots:
            starts_with_root = [
                t for t in ticker_pool if self._ticker_key(t).startswith(f"{root}_")
            ]
            if starts_with_root:
                us_eq = next(
                    (t for t in starts_with_root if self._ticker_key(t).endswith("_US_EQ")),
                    None,
                )
                resolved = us_eq if us_eq is not None else starts_with_root[0]
                self._resolved_ticker_cache[mapped_key] = resolved
                self._resolved_ticker_cache[input_key] = resolved
                return resolved

        raise T212APIError(
            "Could not resolve a tradable Trading 212 ticker "
            f"for input '{ticker}' (mapped '{mapped}')."
        )

    async def resolve_ticker(self, ticker: str) -> str:
        """
        Public resolver used by callers that want startup validation/logging.
        """
        return await self._resolve_ticker(ticker)

    @staticmethod
    def _extract_invalid_qty_precision(error: Exception) -> int | None:
        """
        Parse Trading 212 quantity precision rejection details, e.g.
        `invalid quantity precision 4`.
        """
        match = re.search(r"invalid quantity precision (\d+)", str(error), flags=re.IGNORECASE)
        if not match:
            return None
        try:
            return int(match.group(1))
        except ValueError:
            return None

    @staticmethod
    def _truncate_quantity(qty: float, decimals: int) -> float:
        if decimals <= 0:
            return float(math.trunc(qty))
        factor = 10**decimals
        return math.trunc(qty * factor) / factor

    async def _submit_order_with_precision_fallback(
        self,
        path: str,
        ticker: str,
        qty: float,
        price_key: str | None = None,
        price_value: float | None = None,
        extra_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        mapped_ticker = await self._resolve_ticker(ticker)
        current_qty = float(qty)
        tried_precisions: set[int] = set()
        last_error: T212APIError | None = None

        for _ in range(8):
            payload: dict[str, Any] = {"ticker": mapped_ticker, "quantity": current_qty}
            if price_key is not None and price_value is not None:
                payload[price_key] = price_value
                payload["timeValidity"] = "GOOD_TILL_CANCEL"
            if extra_payload:
                payload.update(extra_payload)

            try:
                return await self._request("POST", path, payload=payload, order_call=True)
            except T212APIError as exc:
                last_error = exc
                invalid_precision = self._extract_invalid_qty_precision(exc)
                if invalid_precision is None:
                    raise

                # Broker reports submitted precision N as invalid; retry with N-1.
                next_precision = max(invalid_precision - 1, 0)
                if next_precision in tried_precisions:
                    break
                tried_precisions.add(next_precision)

                next_qty = self._truncate_quantity(current_qty, next_precision)
                if next_qty == current_qty or next_qty == 0.0:
                    break
                current_qty = next_qty

        if last_error is not None:
            raise last_error
        raise T212APIError(f"POST {path} failed for {ticker}: unknown order submission error.")

    async def __aenter__(self) -> "AsyncT212Client":
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.session is not None:
            await self.session.close()
            self.session = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        order_call: bool = False,
        orders_list_call: bool = False,
    ) -> Any:
        if self.session is None:
            raise RuntimeError("Client session is not initialized. Use 'async with AsyncT212Client(...)'.")
        url = f"{self.base_url}{path}"
        if self.secret_key:
            token = base64.b64encode(f"{self.api_key}:{self.secret_key}".encode("utf-8")).decode("utf-8")
            auth_header = f"Basic {token}"
        else:
            auth_header = f"Bearer {self.api_key}"

        headers = {
            "Authorization": auth_header,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        if orders_list_call:
            limiter = self.orders_list_limiter
        elif order_call:
            limiter = self.order_limiter
        else:
            limiter = self.data_limiter
        retry_idx = 0
        while True:
            await limiter.acquire()
            try:
                req_kwargs: dict[str, Any] = {"headers": headers}
                if payload is not None:
                    req_kwargs["json"] = payload
                async with self.session.request(method=method, url=url, **req_kwargs) as resp:
                    text = await resp.text()
                    if resp.status == 429 and retry_idx < self.max_rate_limit_retries:
                        retry_after_header = resp.headers.get("Retry-After")
                        retry_after_seconds = 0.0
                        if retry_after_header:
                            try:
                                retry_after_seconds = float(retry_after_header)
                            except ValueError:
                                retry_after_seconds = 0.0
                        backoff_seconds = 2**retry_idx
                        await asyncio.sleep(max(backoff_seconds, retry_after_seconds))
                        retry_idx += 1
                        continue

                    if resp.status >= 400:
                        if resp.status == 401 and not self.secret_key:
                            raise T212APIError(
                                f"{method} {path} failed (401): unauthorized. "
                                "Set T212_SECRET_KEY to use Basic auth for Trading 212."
                            )
                        raise T212APIError(f"{method} {path} failed ({resp.status}): {text}")
                    if not text.strip():
                        return {}
                    try:
                        return await resp.json()
                    except aiohttp.ContentTypeError:
                        return {"raw": text}
            except asyncio.TimeoutError as exc:
                raise T212APIError(f"{method} {path} timed out.") from exc
            except aiohttp.ClientError as exc:
                raise T212APIError(f"{method} {path} connection error: {exc}") from exc

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            stripped = value.strip().replace(",", "")
            try:
                return float(stripped)
            except ValueError:
                return None
        return None

    @classmethod
    def _collect_numbers_by_key(cls, obj: Any, out: dict[str, list[float]]) -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                normalized_key = str(key).strip().lower()
                as_num = cls._to_float(value)
                if as_num is not None:
                    out.setdefault(normalized_key, []).append(as_num)
                cls._collect_numbers_by_key(value, out)
        elif isinstance(obj, list):
            for item in obj:
                cls._collect_numbers_by_key(item, out)

    @staticmethod
    def _extract_first_numeric(
        numeric_by_key: dict[str, list[float]], preferred_keys: tuple[str, ...]
    ) -> float | None:
        for key in preferred_keys:
            values = numeric_by_key.get(key, [])
            if values:
                return float(values[0])
        return None

    async def get_equity(self) -> float:
        def _extract_equity(payload: dict[str, Any]) -> tuple[float | None, str]:
            numeric_by_key: dict[str, list[float]] = {}
            self._collect_numbers_by_key(payload, numeric_by_key)

            # Prefer account "total" style values for equity.
            equity = self._extract_first_numeric(
                numeric_by_key,
                preferred_keys=("total", "equity", "totalequity", "netliquidation", "balance"),
            )
            keys_seen = ", ".join(sorted(numeric_by_key.keys())[:20]) or "none"
            return equity, keys_seen

        # Primary endpoint requested by Trading 212 docs/users.
        info_payload = await self._request("GET", "/api/v0/equity/account/info", order_call=False)
        equity, info_keys = _extract_equity(info_payload)
        if equity is not None:
            return equity

        # Fallback endpoint: some API deployments return balances under account/cash.
        cash_payload = await self._request("GET", "/api/v0/equity/account/cash", order_call=False)
        equity, cash_keys = _extract_equity(cash_payload)
        if equity is not None:
            return equity

        raise T212APIError(
            "Equity not found in response payloads. "
            f"Info numeric keys: {info_keys}; Cash numeric keys: {cash_keys}"
        )

    async def get_free_funds(self) -> float:
        """
        Return currently free cash available for new trades.
        Source of truth is /api/v0/equity/account/cash.
        """
        cash_payload = await self._request("GET", "/api/v0/equity/account/cash", order_call=False)
        numeric_by_key: dict[str, list[float]] = {}
        self._collect_numbers_by_key(cash_payload, numeric_by_key)

        free_funds = self._extract_first_numeric(
            numeric_by_key,
            preferred_keys=(
                "free",
                "freefunds",
                "available",
                "availablecash",
                "cashavailable",
                "withdrawable",
            ),
        )
        if free_funds is not None:
            return max(float(free_funds), 0.0)

        # Fallback for schemas that only expose generic cash keys.
        fallback_free = self._extract_first_numeric(
            numeric_by_key,
            preferred_keys=("cash", "funds", "balance"),
        )
        if fallback_free is not None:
            return max(float(fallback_free), 0.0)

        keys_seen = ", ".join(sorted(numeric_by_key.keys())[:20]) or "none"
        raise T212APIError(f"Free funds not found in /account/cash payload. Numeric keys: {keys_seen}")

    async def get_position_quantity(self, ticker: str) -> float:
        """
        Return signed position quantity for a ticker from the live portfolio snapshot.
        Positive means long, negative means short, zero means no open position.
        """
        mapped_ticker = await self._resolve_ticker(ticker)
        payload = await self._request("GET", "/api/v0/equity/portfolio", order_call=False)

        if not isinstance(payload, list):
            return 0.0

        for row in payload:
            if not isinstance(row, dict):
                continue
            row_ticker = str(row.get("ticker", "")).strip()
            if row_ticker != mapped_ticker:
                continue

            qty_raw = row.get("quantity")
            qty = self._to_float(qty_raw)
            if qty is not None:
                return float(qty)
            return 0.0

        return 0.0

    async def resolve_ticker(self, ticker: str) -> str:
        """Expose internal ticker resolution for higher-level reconciliation logic."""
        return await self._resolve_ticker(ticker)

    async def get_portfolio_row(self, ticker: str) -> dict[str, Any] | None:
        """
        Return the broker's portfolio row for this instrument (usually contains quantity and may
        contain average/entry price fields depending on environment/schema).
        """
        mapped_ticker = await self._resolve_ticker(ticker)
        payload = await self._request("GET", "/api/v0/equity/portfolio", order_call=False)
        if not isinstance(payload, list):
            return None
        for row in payload:
            if not isinstance(row, dict):
                continue
            row_ticker = row.get("ticker")
            if row_ticker is None and isinstance(row.get("instrument"), dict):
                row_ticker = row["instrument"].get("ticker")
            if str(row_ticker or "").strip() == mapped_ticker:
                return row
        return None

    async def get_open_position_row(self, ticker: str) -> dict[str, Any] | None:
        """
        Return the broker's open position row for this instrument (includes currentPrice in
        instrument currency). Used to compare last/bid-style broker marks against stop logic.
        """
        mapped_ticker = await self._resolve_ticker(ticker)
        payload = await self._request("GET", "/api/v0/equity/positions", order_call=False)
        if not isinstance(payload, list):
            return None
        for row in payload:
            if not isinstance(row, dict):
                continue
            row_ticker = row.get("ticker")
            if row_ticker is None and isinstance(row.get("instrument"), dict):
                row_ticker = row["instrument"].get("ticker")
            if str(row_ticker or "").strip() == mapped_ticker:
                return row
        return None

    async def get_pending_orders(self) -> list[dict[str, Any]]:
        raw = await self._request(
            "GET",
            "/api/v0/equity/orders",
            order_call=False,
            orders_list_call=True,
        )
        return raw if isinstance(raw, list) else []

    async def fetch_all_paginated_history(
        self,
        first_path: str,
        *,
        page_delay_sec: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        Follow Trading 212 cursor pagination (nextPagePath) until exhausted.
        first_path example: /api/v0/equity/history/orders?limit=50

        History list endpoints are capped at ~6 requests/minute; pass page_delay_sec=10.5
        when pulling many pages to avoid HTTP 429.
        """
        path: str | None = first_path.strip()
        all_items: list[dict[str, Any]] = []
        first = True
        while path:
            if not first and page_delay_sec > 0:
                await asyncio.sleep(page_delay_sec)
            first = False
            payload = await self._request("GET", path, order_call=False)
            if not isinstance(payload, dict):
                break
            items = payload.get("items")
            if isinstance(items, list):
                for it in items:
                    if isinstance(it, dict):
                        all_items.append(it)
            npp = payload.get("nextPagePath")
            path = str(npp).strip() if npp else None
        return all_items

    async def fetch_history_orders(
        self,
        limit: int = 50,
        *,
        page_delay_sec: float = 10.5,
    ) -> list[dict[str, Any]]:
        lim = max(1, min(int(limit), 50))
        return await self.fetch_all_paginated_history(
            f"/api/v0/equity/history/orders?limit={lim}",
            page_delay_sec=page_delay_sec,
        )

    async def fetch_history_transactions(
        self,
        limit: int = 50,
        *,
        page_delay_sec: float = 10.5,
    ) -> list[dict[str, Any]]:
        lim = max(1, min(int(limit), 50))
        return await self.fetch_all_paginated_history(
            f"/api/v0/equity/history/transactions?limit={lim}",
            page_delay_sec=page_delay_sec,
        )

    async def fetch_history_dividends(
        self,
        limit: int = 50,
        *,
        page_delay_sec: float = 10.5,
    ) -> list[dict[str, Any]]:
        lim = max(1, min(int(limit), 50))
        return await self.fetch_all_paginated_history(
            f"/api/v0/equity/history/dividends?limit={lim}",
            page_delay_sec=page_delay_sec,
        )

    async def request_history_export(
        self,
        *,
        time_from: str,
        time_to: str,
        include_orders: bool = True,
        include_transactions: bool = True,
        include_dividends: bool = True,
        include_interest: bool = False,
    ) -> int:
        """
        Request a broker-generated CSV report (async).
        Docs: POST /api/v0/equity/history/exports
        """
        payload = {
            "dataIncluded": {
                "includeDividends": bool(include_dividends),
                "includeInterest": bool(include_interest),
                "includeOrders": bool(include_orders),
                "includeTransactions": bool(include_transactions),
            },
            "timeFrom": str(time_from),
            "timeTo": str(time_to),
        }
        resp = await self._request(
            "POST",
            "/api/v0/equity/history/exports",
            payload=payload,
            order_call=False,
        )
        if not isinstance(resp, dict) or "reportId" not in resp:
            raise T212APIError(f"Unexpected response from history/exports: {resp}")
        return int(resp["reportId"])

    async def list_history_exports(self) -> list[dict[str, Any]]:
        """
        List requested reports and their status.
        Docs: GET /api/v0/equity/history/exports
        """
        resp = await self._request("GET", "/api/v0/equity/history/exports", order_call=False)
        return resp if isinstance(resp, list) else []

    async def place_stop_order(
        self,
        ticker: str,
        qty: float,
        stop_price: float,
        *,
        extended_hours: bool | None = None,
    ) -> dict[str, Any]:
        extra: dict[str, Any] | None = None
        if extended_hours is True:
            extra = {"extendedHours": True}
        return await self._submit_order_with_precision_fallback(
            path="/api/v0/equity/orders/stop",
            ticker=ticker,
            qty=qty,
            price_key="stopPrice",
            price_value=stop_price,
            extra_payload=extra,
        )

    async def place_limit_order(self, ticker: str, qty: float, limit_price: float) -> dict[str, Any]:
        return await self._submit_order_with_precision_fallback(
            path="/api/v0/equity/orders/limit",
            ticker=ticker,
            qty=qty,
            price_key="limitPrice",
            price_value=limit_price,
        )

    async def close_position(self, ticker: str, qty: float) -> dict[str, Any]:
        # Closing is done by submitting an opposite-side market order via signed quantity.
        return await self._submit_order_with_precision_fallback(
            path="/api/v0/equity/orders/market",
            ticker=ticker,
            qty=qty,
        )

    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        return await self._request("DELETE", f"/api/v0/equity/orders/{order_id}", order_call=True)
