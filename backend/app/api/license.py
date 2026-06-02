from __future__ import annotations

import uuid

import httpx
from fastapi import APIRouter

from app.integrations.supabase_rest import SupabaseRest
from app.services.license_tier import resolve_license_tier

router = APIRouter(prefix="/api/license", tags=["license"])


@router.get("/validate")
async def validate_license(key: str) -> dict:
    """
    Validate a license key and return its effective subscription tier.

    Response: {"valid": bool, "tier": "pro" | "trial" | "expired" | "invalid", "message": str}

    `valid` is True for `pro` and `trial` (the app may run); False for
    `expired` (trial ended) and `invalid` (bad/revoked key).

    Read-only — does NOT update last_ip_address or any row data.
    """
    try:
        license_key = uuid.UUID(key.strip())
    except Exception:
        return {
            "valid": False,
            "tier": "invalid",
            "message": "Invalid license key format. It should look like: 550e8400-e29b-41d4-a716-446655440000",
        }

    sb = SupabaseRest.from_settings()
    if sb is None:
        return {
            "valid": False,
            "tier": "invalid",
            "message": "Validation service unavailable — backend is missing Supabase credentials.",
        }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            tier, _lic, message = await resolve_license_tier(sb, client, license_key)
    except httpx.HTTPError as exc:
        return {
            "valid": False,
            "tier": "invalid",
            "message": f"Network error contacting Supabase: {exc}",
        }
    except Exception as exc:
        return {
            "valid": False,
            "tier": "invalid",
            "message": f"Validation error: {exc}",
        }

    # pro/trial → app may run; expired/invalid → blocked.
    valid = tier in ("pro", "trial")
    return {"valid": valid, "tier": tier, "message": message}
