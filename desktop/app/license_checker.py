from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

import aiohttp


# The three possible outcomes from the validation endpoint.
TierType = Literal["pro", "free", "invalid"]


@dataclass
class LicenseResult:
    valid: bool
    tier: TierType
    message: str


def _build_validate_url(ws_url: str) -> str:
    """
    Derive the HTTP validate URL from the WebSocket server URL.
    e.g. ws://127.0.0.1:8010/ws/exec  →  http://127.0.0.1:8010/api/license/validate
    """
    try:
        p = urlparse(ws_url.strip())
        if p.scheme in ("ws", "wss") and p.hostname:
            http_scheme = "https" if p.scheme == "wss" else "http"
            netloc = f"{p.hostname}:{p.port}" if p.port else str(p.hostname)
            return f"{http_scheme}://{netloc}/api/license/validate"
    except Exception:
        pass
    return "http://127.0.0.1:8010/api/license/validate"


async def check_license(license_key: str, ws_url: str) -> LicenseResult:
    """
    Call the backend /api/license/validate endpoint and return a LicenseResult.

    Never raises — always returns a result even on network errors.
    """
    key = license_key.strip()
    if not key:
        return LicenseResult(
            valid=False,
            tier="invalid",
            message="No license key entered.",
        )

    url = _build_validate_url(ws_url)
    try:
        timeout = aiohttp.ClientTimeout(total=12.0)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params={"key": key}) as resp:
                if resp.status != 200:
                    return LicenseResult(
                        valid=False,
                        tier="invalid",
                        message=f"Validation server returned HTTP {resp.status}.",
                    )
                data: dict = await resp.json()
                return LicenseResult(
                    valid=bool(data.get("valid", False)),
                    tier=data.get("tier", "invalid"),  # type: ignore[arg-type]
                    message=str(data.get("message", "No message returned.")),
                )
    except aiohttp.ClientConnectorError:
        return LicenseResult(
            valid=False,
            tier="invalid",
            message="Cannot reach the backend server. Make sure it is running.",
        )
    except Exception as exc:
        return LicenseResult(
            valid=False,
            tier="invalid",
            message=f"Validation failed: {exc}",
        )
