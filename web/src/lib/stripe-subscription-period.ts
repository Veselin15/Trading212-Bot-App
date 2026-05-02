import type Stripe from "stripe";

/**
 * Stripe Basil+ (e.g. API 2026-04-22.dahlia): `current_period_end` lives on subscription items, not on the subscription root.
 * Still read legacy top-level field when present (older API versions / expanded objects).
 */
export function getStripeSubscriptionPeriodEndUnix(sub: Stripe.Subscription): number | null {
  const items = sub.items?.data;
  if (Array.isArray(items) && items.length > 0) {
    let maxEnd = 0;
    for (const item of items) {
      const end = (item as Stripe.SubscriptionItem & { current_period_end?: number }).current_period_end;
      if (typeof end === "number" && Number.isFinite(end) && end > maxEnd) maxEnd = end;
    }
    if (maxEnd > 0) return maxEnd;
  }

  const legacy = (sub as Stripe.Subscription & { current_period_end?: number }).current_period_end;
  if (typeof legacy === "number" && Number.isFinite(legacy) && legacy > 0) return legacy;

  return null;
}
