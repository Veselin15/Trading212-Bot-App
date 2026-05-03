from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter

from app.integrations.supabase_rest import SupabaseRest

router = APIRouter(prefix="/api/license", tags=["license"])


@router.get("/validate")
async def validate_license(key: str) -> dict:
    """
    Validate a license key and return its subscription tier.

    Response: {"valid": bool, "tier": "pro" | "free" | "invalid", "message": str}

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

    now = datetime.now(tz=UTC)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1. Fetch the license row (read-only; no IP update here).
            lic_rows = await sb.get(
                client,
                f"licenses?select=id,user_id,status,revoked_at,expires_at&license_key=eq.{license_key}",
            )
            lic = lic_rows[0] if lic_rows else None

            if not lic or lic.get("revoked_at") is not None:
                return {
                    "valid": False,
                    "tier": "invalid",
                    "message": "License key not found or has been revoked.",
                }

            if str(lic.get("status") or "inactive") != "active":
                return {
                    "valid": False,
                    "tier": "invalid",
                    "message": "License key is inactive.",
                }

            expires_at = lic.get("expires_at")
            if expires_at:
                try:
                    exp = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
                    if exp <= now:
                        return {
                            "valid": False,
                            "tier": "invalid",
                            "message": "License key has expired. Renew your subscription on the website.",
                        }
                except Exception:
                    return {
                        "valid": False,
                        "tier": "invalid",
                        "message": "License key expiry could not be parsed — treat as expired.",
                    }

            user_id = str(lic.get("user_id") or "").strip()
            if not user_id:
                return {
                    "valid": False,
                    "tier": "invalid",
                    "message": "License key has no associated account.",
                }

            # 2. Check the latest subscription for this user to determine tier.
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
                            return {
                                "valid": True,
                                "tier": "pro",
                                "message": "Pro License validated. Live trading unlocked.",
                            }
                    except Exception:
                        pass
                else:
                    # Active subscription with no end-date cap — treat as pro.
                    return {
                        "valid": True,
                        "tier": "pro",
                        "message": "Pro License validated. Live trading unlocked.",
                    }

            # License is valid but no active subscription → free / paper-only tier.
            return {
                "valid": True,
                "tier": "free",
                "message": "Free Demo License active. Live trading disabled. Upgrade on the website.",
            }

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
