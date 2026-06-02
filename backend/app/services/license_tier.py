from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import httpx

from app.integrations.supabase_rest import SupabaseRest


def _parse_ts(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


async def resolve_license_tier(
    sb: SupabaseRest,
    client: httpx.AsyncClient,
    license_key: uuid.UUID,
    *,
    now: datetime | None = None,
) -> tuple[str, dict[str, Any] | None, str]:
    """
    Resolve the effective subscription tier for a portal license key.

    Returns ``(tier, license_row, message)`` where *tier* is one of:
      ``pro``     – active Pro subscription; live trading + full signal feed.
      ``starter`` – active Starter subscription; live trading + core signals only.
      ``trial``   – inside the 14-day free trial; paper trading + full feed.
      ``expired`` – trial ended (or subscription lapsed) and no active plan.
      ``invalid`` – key not found / revoked / malformed.

    Effective tier mirrors ``public.effective_tier`` in SQL:
        active subscription, plan=pro      -> pro
        active subscription, plan=starter  -> starter
        active subscription, plan=null     -> pro      (legacy single-price)
        else trial_ends_at in future       -> trial
        else                               -> expired
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

    # Optional hard expiry stamped on the license row itself.
    exp = _parse_ts(lic.get("expires_at"))
    if exp is not None and exp <= now:
        return "invalid", None, "License key has expired. Renew your subscription on the website."

    user_id = str(lic.get("user_id") or "").strip()
    if not user_id:
        return "invalid", None, "License key has no associated account."

    # 1) Active paid subscription -> PRO or STARTER (by plan).
    sub_rows = await sb.get(
        client,
        "subscriptions?select=status,current_period_end,plan"
        f"&user_id=eq.{user_id}&order=created_at.desc&limit=1",
    )
    sub = sub_rows[0] if sub_rows else None
    if sub and str(sub.get("status") or "") == "active":
        cpe = _parse_ts(sub.get("current_period_end"))
        if cpe is None or cpe > now:
            plan = str(sub.get("plan") or "").strip().lower()
            if plan == "starter":
                return (
                    "starter",
                    lic,
                    "Starter subscription validated. Live trading on core signals "
                    "(up to 3 open positions).",
                )
            return (
                "pro",
                lic,
                "Pro subscription validated. Live trading on the full signal feed "
                "(up to 10 open positions).",
            )

    # 2) Unexpired trial -> TRIAL.
    prof_rows = await sb.get(
        client,
        f"profiles?select=trial_ends_at,subscription_tier&user_id=eq.{user_id}&limit=1",
    )
    prof = prof_rows[0] if prof_rows else None
    if prof:
        trial_ends = _parse_ts(prof.get("trial_ends_at"))
        if trial_ends is not None and trial_ends > now:
            days_left = max(1, (trial_ends - now).days + 1)
            return (
                "trial",
                lic,
                f"Free trial active — {days_left} day(s) left. Paper trading only; "
                "upgrade to unlock live execution.",
            )

    # 3) Otherwise -> EXPIRED.
    return (
        "expired",
        lic,
        "Your free trial has ended. Upgrade at swifttrade.app to resume.",
    )
