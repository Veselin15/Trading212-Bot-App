from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings


@dataclass(frozen=True)
class SupabaseRest:
    url: str
    service_role_key: str

    @classmethod
    def from_settings(cls) -> "SupabaseRest | None":
        if not settings.supabase_url or not settings.supabase_service_role_key:
            return None
        return cls(url=settings.supabase_url, service_role_key=settings.supabase_service_role_key)

    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.service_role_key,
            "authorization": f"Bearer {self.service_role_key}",
        }

    def _base(self) -> str:
        return f"{self.url.rstrip('/')}/rest/v1"

    async def get(self, client: httpx.AsyncClient, path: str) -> list[dict[str, Any]]:
        resp = await client.get(f"{self._base()}/{path.lstrip('/')}", headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else []

    async def patch(self, client: httpx.AsyncClient, path: str, patch: dict[str, Any]) -> None:
        resp = await client.patch(
            f"{self._base()}/{path.lstrip('/')}",
            headers={**self._headers(), "prefer": "return=minimal"},
            json=patch,
        )
        resp.raise_for_status()

