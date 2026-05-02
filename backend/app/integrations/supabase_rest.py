from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from app.core.config import _BACKEND_ENV, settings
from app.core.env_paths import backend_dotenv_candidate_paths


def _backend_dotenv_candidates() -> list[Path]:
    return backend_dotenv_candidate_paths(_BACKEND_ENV)


def _parse_dotenv_manual(path: Path) -> dict[str, str]:
    """Last-resort KEY=VALUE parse if python-dotenv cannot read the file."""
    out: dict[str, str] = {}
    try:
        raw = path.read_bytes()
    except OSError:
        return out
    text: str | None = None
    for encoding in ("utf-8-sig", "utf-8", "utf-16-le", "utf-16-be", "cp1252"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        return out
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, _, val = s.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key:
            out[key] = val
    return out


def _read_single_env_file(path: Path) -> dict[str, str]:
    flat: dict[str, str] = {}
    try:
        from dotenv import dotenv_values

        vals = dotenv_values(path, encoding="utf-8-sig")
        for k, v in vals.items():
            if k is None:
                continue
            nk = str(k).strip().lstrip("\ufeff")
            flat[nk] = "" if v is None else str(v)
    except Exception:
        flat = {}
    if (flat.get("SUPABASE_URL") or "").strip() and (flat.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip():
        return flat
    manual = _parse_dotenv_manual(path)
    for k, v in manual.items():
        flat.setdefault(k, v)
    return flat


def _read_backend_env_flat() -> dict[str, str]:
    merged: dict[str, str] = {}
    for path in _backend_dotenv_candidates():
        if not path.is_file():
            continue
        chunk = _read_single_env_file(path)
        for k, v in chunk.items():
            merged.setdefault(k, v)
    return merged


def supabase_config_smoke_dict() -> dict[str, Any]:
    """Safe diagnostics (lengths only)."""
    flat = _read_backend_env_flat()
    url, key = _supabase_credentials()
    cands = _backend_dotenv_candidates()
    return {
        "process_pid": os.getpid(),
        "primary_backend_dotenv": str(_BACKEND_ENV),
        "primary_exists": _BACKEND_ENV.is_file(),
        "candidates": [{"path": str(p), "exists": p.is_file()} for p in cands],
        "settings_url_len": len((settings.supabase_url or "").strip()),
        "settings_key_len": len((settings.supabase_service_role_key or "").strip()),
        "file_url_len": len((flat.get("SUPABASE_URL") or "").strip()),
        "file_key_len": len((flat.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()),
        "resolved_url_len": len(url),
        "resolved_key_len": len(key),
    }


def _supabase_credentials() -> tuple[str, str]:
    """Resolve URL + service key: process env first, then merged ``.env`` files, then ``settings``."""
    flat = _read_backend_env_flat()
    url = (os.environ.get("SUPABASE_URL") or "").strip()
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url:
        url = (flat.get("SUPABASE_URL") or "").strip()
    if not key:
        key = (flat.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url:
        url = (flat.get("NEXT_PUBLIC_SUPABASE_URL") or "").strip()
    if not url:
        url = (settings.supabase_url or "").strip()
    if not key:
        key = (settings.supabase_service_role_key or "").strip()
    return url, key


@dataclass(frozen=True)
class SupabaseRest:
    url: str
    service_role_key: str

    @classmethod
    def from_settings(cls) -> "SupabaseRest | None":
        url, key = _supabase_credentials()
        su = str(url or "").strip()
        sk = str(key or "").strip()
        if len(su) == 0 or len(sk) == 0:
            return None
        return cls(url=su, service_role_key=sk)

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

