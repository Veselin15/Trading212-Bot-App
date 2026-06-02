import type Stripe from "stripe";

import type { PaidPlan } from "@/lib/subscription-model";

/**
 * Stripe price <-> paid-plan mapping. The two tiers are configured via env:
 *   STRIPE_PRICE_ID_STARTER  – €19/mo Starter price id
 *   STRIPE_PRICE_ID_PRO      – €49/mo Pro price id
 *
 * `STRIPE_PRICE_ID` is honoured as a legacy fallback for the Pro price so existing
 * single-price installs keep working.
 */

export function starterPriceId(): string | null {
  return (process.env.STRIPE_PRICE_ID_STARTER || "").trim() || null;
}

export function proPriceId(): string | null {
  return (process.env.STRIPE_PRICE_ID_PRO || process.env.STRIPE_PRICE_ID || "").trim() || null;
}

export function priceIdForPlan(plan: PaidPlan): string | null {
  return plan === "starter" ? starterPriceId() : proPriceId();
}

/** Resolve a Stripe price id back to our plan. Unknown ids default to PRO (full access). */
export function planFromPriceId(priceId: string | null | undefined): PaidPlan {
  const id = (priceId || "").trim();
  if (id && id === starterPriceId()) return "starter";
  return "pro";
}

/** Extract the first line-item price id from a Stripe subscription, if expanded. */
export function priceIdFromStripeSubscription(sub: Stripe.Subscription): string | null {
  const item = sub.items?.data?.[0];
  const price = item?.price;
  if (!price) return null;
  return typeof price === "string" ? price : price.id ?? null;
}

/** Resolve the plan a Stripe subscription is on (defaults to PRO when unknown). */
export function planFromStripeSubscription(sub: Stripe.Subscription): PaidPlan {
  return planFromPriceId(priceIdFromStripeSubscription(sub));
}

/** Whether the given plan can be checked out (its price id is configured). */
export function isPlanCheckoutConfigured(plan: PaidPlan): boolean {
  return Boolean(process.env.STRIPE_SECRET_KEY && priceIdForPlan(plan));
}
