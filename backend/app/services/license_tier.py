from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import httpx

from app.integrations.supabase_rest import SupabaseRest


async def resolve_license_tier(
    sb: SupabaseRest,
    client: httpx.AsyncClient,
    license_key: uuid.UUID,
    *,
    now: datetime | None = None,
) -> tuple[str, dict[str, Any] | None, str]:
    """
    Resolve subscription tier for a portal license key.

    Returns ``(tier, license_row, message)`` where *tier* is ``pro``, ``free``, or ``invalid``.
    """
    now = now or datetime.now(tz=UTC)

    lic_rows = await sb.get(
        client,
        f"licenses?select=id,user_id,status,revoked_at,expires_at&license_key=eq.{license_key}",
    )
    lic = lic_rows[0] if lic_rows else None

    if not lic or lic.get("revoked_at") is not None:
        return "invalid", None, "License key not found or has been revoked."

    if str(lic.get("status") or "inactive") != "active":
        return "invalid", None, "License key is inactive."

    expires_at = lic.get("expires_at")
    if expires_at:
        try:
            exp = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            if exp <= now:
                return "invalid", None, "License key has expired. Renew your subscription on the website."
        except Exception:
            return "invalid", None, "License key expiry could not be parsed — treat as expired."

    user_id = str(lic.get("user_id") or "").strip()
    if not user_id:
        return "invalid", None, "License key has no associated account."

    sub_rows = await sb.get(
        client,
        "subscriptions?select=status,current_period_end"
        f"&user_id=eq.{user_id}&order=created_at.desc&limit=1",
    )
    sub = sub_rows[0] if sub_rows else None

    if sub and str(sub.get("status") or "") == "active":
        cpe = sub.get("current_period_end")
        if cpe:
            try:
                end = datetime.fromisoformat(str(cpe).replace("Z", "+00:00"))
                if end > now:
                    return "pro", lic, "Pro License validated. Live trading unlocked."
            except Exception:
                pass
        else:
            return "pro", lic, "Pro License validated. Live trading unlocked."

    return (
        "free",
        lic,
        "Free Demo License active. Live trading disabled. Upgrade on the website.",
    )
