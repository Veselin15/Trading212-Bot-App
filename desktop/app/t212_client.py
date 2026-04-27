from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass
from typing import Any

import aiohttp


@dataclass(frozen=True)
class T212Keys:
    api_key: str
    secret_key: str | None = None


class T212Client:
    def __init__(self, *, keys: T212Keys, base_url: str = "https://demo.trading212.com") -> None:
        self._keys = keys
        self._base_url = base_url.rstrip("/")
        self._session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> "T212Client":
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20))
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    def _auth_header(self) -> str:
        if self._keys.secret_key:
            token = base64.b64encode(f"{self._keys.api_key}:{self._keys.secret_key}".encode("utf-8")).decode("utf-8")
            return f"Basic {token}"
        return f"Bearer {self._keys.api_key}"

    async def _request(self, method: str, path: str, *, payload: dict[str, Any] | None = None) -> Any:
        if not self._session:
            raise RuntimeError("T212Client not started")

        url = f"{self._base_url}{path}"
        headers = {"Authorization": self._auth_header(), "Accept": "application/json", "Content-Type": "application/json"}

        backoff = 1.0
        for attempt in range(8):
            async with self._session.request(method, url, json=payload, headers=headers) as resp:
                if resp.status == 429:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2.0, 30.0)
                    continue
                text = await resp.text()
                if resp.status >= 400:
                    raise RuntimeError(f"T212 error {resp.status}: {text[:500]}")
                if "application/json" in (resp.headers.get("content-type") or ""):
                    return await resp.json()
                return text
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2.0, 30.0)

        raise RuntimeError("T212 request failed after retries")

    async def get_price(self, symbol: str) -> float:
        # Placeholder: implement against your actual Trading212 endpoint once confirmed.
        # For now, this is a stub that keeps the position manager structure in place.
        raise NotImplementedError("Implement Trading212 price endpoint mapping for symbol->instrument")

