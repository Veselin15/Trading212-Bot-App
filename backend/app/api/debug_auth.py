from __future__ import annotations

from fastapi import Header, HTTPException

from app.core.config import settings


def require_debug_api_key(x_debug_key: str | None = Header(default=None, alias="X-Debug-Key")) -> None:
    """When debug_api_key is set, all /debug routes require the matching header."""
    expected = (settings.debug_api_key or "").strip()
    if not expected:
        return
    if (x_debug_key or "").strip() != expected:
        raise HTTPException(status_code=403, detail="Invalid or missing X-Debug-Key")
