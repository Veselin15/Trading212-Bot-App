from __future__ import annotations

from datetime import UTC, datetime, timedelta

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import License, LicenseStatus, User
from app.db.session import db_session


router = APIRouter(prefix="/webhooks/stripe", tags=["stripe"])


def _invoice_period_end_utc(invoice: stripe.Invoice) -> datetime | None:
    try:
        # Best effort: use subscription line period end if present.
        lines = getattr(invoice, "lines", None)
        data = getattr(lines, "data", None) if lines else None
        if data and len(data) > 0 and getattr(data[0], "period", None):
            end_ts = getattr(data[0].period, "end", None)
            if isinstance(end_ts, int):
                return datetime.fromtimestamp(end_ts, tz=UTC)
    except Exception:
        return None
    return None


async def _activate_or_extend_license(*, session: AsyncSession, user: User, new_expiry: datetime) -> License:
    # If user has a non-revoked license, extend the latest one; otherwise create a new license.
    q = (
        select(License)
        .where(License.user_id == user.id)
        .where(License.revoked_at.is_(None))
        .order_by(License.expires_at.desc())
        .limit(1)
    )
    existing = (await session.execute(q)).scalar_one_or_none()
    if existing is None:
        lic = License(user_id=user.id, status=LicenseStatus.active, expires_at=new_expiry)
        session.add(lic)
        await session.flush()
        return lic

    if existing.expires_at < new_expiry:
        existing.expires_at = new_expiry
    existing.status = LicenseStatus.active
    await session.flush()
    return existing


async def _suspend_licenses(*, session: AsyncSession, user: User) -> int:
    q = select(License).where(License.user_id == user.id).where(License.revoked_at.is_(None))
    licenses = (await session.execute(q)).scalars().all()
    for lic in licenses:
        if lic.status != LicenseStatus.expired:
            lic.status = LicenseStatus.suspended
    await session.flush()
    return len(licenses)


@router.post("")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    session: AsyncSession = Depends(db_session),
):
    stripe.api_key = settings.stripe_secret_key or None
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=500, detail="Stripe webhook secret not configured")
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    raw = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload=raw,
            sig_header=stripe_signature,
            secret=settings.stripe_webhook_secret,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid webhook signature: {exc}")

    event_type = event["type"]
    obj = event["data"]["object"]

    # We only implement invoice-based flows first; can be extended to subscriptions later.
    if event_type in {"invoice.payment_succeeded", "invoice.payment_failed"}:
        invoice = stripe.Invoice.construct_from(obj, stripe.api_key)
        customer_id = getattr(invoice, "customer", None)
        if not isinstance(customer_id, str) or not customer_id:
            raise HTTPException(status_code=400, detail="Invoice missing customer id")

        user = (
            await session.execute(select(User).where(User.stripe_customer_id == customer_id).limit(1))
        ).scalar_one_or_none()
        if user is None:
            # We don't auto-create users here because the portal owns account creation.
            raise HTTPException(status_code=404, detail="No user for stripe_customer_id")

        if event_type == "invoice.payment_succeeded":
            period_end = _invoice_period_end_utc(invoice)
            new_expiry = period_end or (datetime.now(tz=UTC) + timedelta(days=30))
            lic = await _activate_or_extend_license(session=session, user=user, new_expiry=new_expiry)
            await session.commit()
            return {"ok": True, "action": "activated", "license_id": str(lic.id), "expires_at": lic.expires_at.isoformat()}

        if event_type == "invoice.payment_failed":
            n = await _suspend_licenses(session=session, user=user)
            await session.commit()
            return {"ok": True, "action": "suspended", "licenses_touched": n}

    # Unknown event types should still 2xx so Stripe doesn't retry forever.
    return {"ok": True, "ignored": True, "type": event_type}

