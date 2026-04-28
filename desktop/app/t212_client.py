from __future__ import annotations

import asyncio
import base64
import math
import re
import time
from dataclasses import dataclass
from typing import Any

import aiohttp


class T212APIError(RuntimeError):
    pass


@dataclass(frozen=True)
class T212Keys:
    api_key: str
    secret_key: str | None = None


@dataclass
class AsyncTokenBucket:
    capacity: int
    refill_rate_per_sec: float

    def __post_init__(self) -> None:
        self._tokens = float(self.capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._last_refill = now
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate_per_sec)

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


class T212Client:
    def __init__(self, *, keys: T212Keys, base_url: str = "https://demo.trading212.com", timeout_seconds: int = 20) -> None:
        if not keys.api_key:
            raise EnvironmentError("Missing Trading212 API key.")
        self._keys = keys
        self._base_url = base_url.rstrip("/")
        self._timeout = aiohttp.ClientTimeout(total=int(timeout_seconds))
        self._session: aiohttp.ClientSession | None = None

        self._order_limiter = AsyncTokenBucket(capacity=50, refill_rate_per_sec=50.0 / 60.0)
        self._data_limiter = AsyncTokenBucket(capacity=1, refill_rate_per_sec=1.0)
        self._orders_list_limiter = AsyncTokenBucket(capacity=1, refill_rate_per_sec=1.0 / 5.2)

        self._resolved_ticker_cache: dict[str, str] = {}
        self._instrument_ticker_index: dict[str, str] | None = None
        self._instrument_row_by_ticker_upper: dict[str, dict[str, Any]] | None = None
        self._ticker_lock = asyncio.Lock()

    async def __aenter__(self) -> "T212Client":
        self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    def _auth_header(self) -> str:
        if self._keys.secret_key:
            token = base64.b64encode(f"{self._keys.api_key}:{self._keys.secret_key}".encode("utf-8")).decode("utf-8")
            return f"Basic {token}"
        return f"Bearer {self._keys.api_key}"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        order_call: bool = False,
        orders_list_call: bool = False,
    ) -> Any:
        if self._session is None:
            raise RuntimeError("Client session is not initialized.")

        url = f"{self._base_url}{path}"
        headers = {"Authorization": self._auth_header(), "Content-Type": "application/json", "Accept": "application/json"}

        limiter = self._data_limiter
        if orders_list_call:
            limiter = self._orders_list_limiter
        elif order_call:
            limiter = self._order_limiter

        retry_idx = 0
        while True:
            await limiter.acquire()
            try:
                async with self._session.request(method=method, url=url, json=payload, headers=headers) as resp:
                    text = await resp.text()
                    if resp.status == 429 and retry_idx < 6:
                        retry_after_header = resp.headers.get("Retry-After")
                        retry_after_seconds = 0.0
                        if retry_after_header:
                            try:
                                retry_after_seconds = float(retry_after_header)
                            except ValueError:
                                retry_after_seconds = 0.0
                        backoff_seconds = 2**retry_idx
                        await asyncio.sleep(max(backoff_seconds, retry_after_seconds, 1.0))
                        retry_idx += 1
                        continue

                    if resp.status >= 400:
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
    def _ticker_key(ticker: str) -> str:
        return str(ticker).strip().upper()

    async def _load_instrument_ticker_index(self) -> dict[str, str]:
        if self._instrument_ticker_index is not None:
            return self._instrument_ticker_index

        async with self._ticker_lock:
            if self._instrument_ticker_index is not None:
                return self._instrument_ticker_index
            instruments = await self._request("GET", "/api/v0/equity/metadata/instruments", order_call=False)
            if not isinstance(instruments, list):
                raise T212APIError("Unexpected metadata format from /api/v0/equity/metadata/instruments.")

            ticker_by_upper: dict[str, str] = {}
            row_by_upper: dict[str, dict[str, Any]] = {}
            for row in instruments:
                if not isinstance(row, dict):
                    continue
                raw_ticker = str(row.get("ticker", "")).strip()
                if raw_ticker:
                    upper = self._ticker_key(raw_ticker)
                    ticker_by_upper[upper] = raw_ticker
                    row_by_upper[upper] = row
            if not ticker_by_upper:
                raise T212APIError("No tradable instruments returned by /api/v0/equity/metadata/instruments.")
            self._instrument_ticker_index = ticker_by_upper
            self._instrument_row_by_ticker_upper = row_by_upper
            return self._instrument_ticker_index

    async def get_instrument_row(self, ticker: str) -> dict[str, Any] | None:
        mapped = await self.resolve_ticker(ticker)
        await self._load_instrument_ticker_index()
        if not self._instrument_row_by_ticker_upper:
            return None
        return self._instrument_row_by_ticker_upper.get(self._ticker_key(mapped))

    async def get_market_state(self, ticker: str) -> str:
        row = await self.get_instrument_row(ticker)
        if not row:
            return "unknown"
        for key in ("marketState", "market_status", "marketStatus", "tradingStatus", "trading_state", "status"):
            v = row.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
        # Common fallbacks
        if isinstance(row.get("tradable"), bool):
            return "tradable" if row["tradable"] else "not_tradable"
        if isinstance(row.get("isTradable"), bool):
            return "tradable" if row["isTradable"] else "not_tradable"
        return "unknown"

    @staticmethod
    def _extract_symbol_root(raw_ticker: str) -> str:
        upper = str(raw_ticker).strip().upper()
        if not upper:
            return ""
        for sep in ("_", "."):
            if sep in upper:
                return upper.split(sep, 1)[0]
        return upper

    async def resolve_ticker(self, ticker: str) -> str:
        mapped_key = self._ticker_key(ticker)
        if mapped_key in self._resolved_ticker_cache:
            return self._resolved_ticker_cache[mapped_key]

        ticker_by_upper = await self._load_instrument_ticker_index()
        direct_match = ticker_by_upper.get(mapped_key)
        if direct_match:
            self._resolved_ticker_cache[mapped_key] = direct_match
            return direct_match

        # Yahoo-style root.EX -> ROOT{ex_first_letter}_EQ
        if "." in mapped_key:
            root, market = mapped_key.split(".", 1)
            if root and market:
                cand = f"{root}{market[0]}_EQ"
                match = ticker_by_upper.get(cand)
                if match:
                    self._resolved_ticker_cache[mapped_key] = match
                    return match

        root = self._extract_symbol_root(mapped_key)
        for t in ticker_by_upper.values():
            if self._extract_symbol_root(t) == root:
                self._resolved_ticker_cache[mapped_key] = t
                return t

        raise T212APIError(f"Could not resolve ticker '{ticker}' to a tradable instrument.")

    @staticmethod
    def _extract_invalid_qty_precision(error: Exception) -> int | None:
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
        *,
        price_key: str | None = None,
        price_value: float | None = None,
        extra_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        mapped_ticker = await self.resolve_ticker(ticker)
        current_qty = float(qty)
        tried_precisions: set[int] = set()
        last_error: T212APIError | None = None

        for _ in range(8):
            payload: dict[str, Any] = {"ticker": mapped_ticker, "quantity": current_qty}
            if price_key is not None and price_value is not None:
                payload[price_key] = float(price_value)
                payload["timeValidity"] = "GOOD_TILL_CANCEL"
            if extra_payload:
                payload.update(extra_payload)
            try:
                resp = await self._request("POST", path, payload=payload, order_call=True)
                return resp if isinstance(resp, dict) else {"raw": resp}
            except T212APIError as exc:
                last_error = exc
                invalid_precision = self._extract_invalid_qty_precision(exc)
                if invalid_precision is None:
                    raise
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

    async def get_free_funds(self) -> float:
        payload = await self._request("GET", "/api/v0/equity/account/cash", order_call=False)
        if not isinstance(payload, dict):
            return 0.0
        for key in ("free", "freeFunds", "available", "availableCash", "cash", "balance"):
            if key in payload:
                try:
                    return max(float(payload[key]), 0.0)
                except Exception:
                    pass
        return 0.0

    async def get_portfolio(self) -> list[dict[str, Any]]:
        payload = await self._request("GET", "/api/v0/equity/portfolio", order_call=False)
        return payload if isinstance(payload, list) else []

    async def get_positions(self) -> list[dict[str, Any]]:
        payload = await self._request("GET", "/api/v0/equity/positions", order_call=False)
        return payload if isinstance(payload, list) else []

    async def get_pending_orders(self) -> list[dict[str, Any]]:
        payload = await self._request("GET", "/api/v0/equity/orders", order_call=False, orders_list_call=True)
        return payload if isinstance(payload, list) else []

    async def get_position_quantity(self, ticker: str) -> float:
        mapped = await self.resolve_ticker(ticker)
        for row in await self.get_portfolio():
            if not isinstance(row, dict):
                continue
            row_ticker = row.get("ticker")
            if row_ticker is None and isinstance(row.get("instrument"), dict):
                row_ticker = row["instrument"].get("ticker")
            if str(row_ticker or "").strip() != mapped:
                continue
            qty_raw = row.get("quantity")
            try:
                return float(qty_raw)
            except Exception:
                return 0.0
        return 0.0

    async def place_market_order(self, ticker: str, qty: float) -> dict[str, Any]:
        return await self._submit_order_with_precision_fallback("/api/v0/equity/orders/market", ticker, qty)

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
            "/api/v0/equity/orders/stop",
            ticker,
            qty,
            price_key="stopPrice",
            price_value=stop_price,
            extra_payload=extra,
        )

    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        resp = await self._request("DELETE", f"/api/v0/equity/orders/{order_id}", order_call=True)
        return resp if isinstance(resp, dict) else {"raw": resp}

    async def close_position(self, ticker: str) -> dict[str, Any]:
        qty = await self.get_position_quantity(ticker)
        if qty == 0.0:
            return {"ok": True, "skipped": True, "reason": "no_position"}
        return await self.place_market_order(ticker, qty=-qty)

    async def get_price_from_positions(self, ticker: str) -> float | None:
        mapped = await self.resolve_ticker(ticker)
        for row in await self.get_positions():
            if not isinstance(row, dict):
                continue
            row_ticker = str(row.get("ticker") or "").strip()
            if not row_ticker and isinstance(row.get("instrument"), dict):
                row_ticker = str(row["instrument"].get("ticker") or "").strip()
            if row_ticker != mapped:
                continue
            for key in ("currentPrice", "current_price", "price"):
                if key in row:
                    try:
                        return float(row[key])
                    except Exception:
                        pass
        return None

