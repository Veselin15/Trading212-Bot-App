export type PaidPlan = "starter" | "pro";

export type SubscriptionRow = {
  status: string;
  current_period_end: string | null;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  plan?: string | null;
};

/**
 * Resolve the paid plan of an *active* subscription.
 * A null `plan` (legacy single-price installs) is treated as PRO.
 */
export function activePaidPlan(row: SubscriptionRow | null): PaidPlan | null {
  if (!canUseProFeatures(row)) return null;
  return row?.plan === "starter" ? "starter" : "pro";
}

/** True while `current_period_end` is in the future (informational / past_due grace only). */
export function subscriptionPeriodStillOpen(row: SubscriptionRow | null): boolean {
  if (!row?.current_period_end) return false;
  const end = new Date(row.current_period_end).getTime();
  return Number.isFinite(end) && end > Date.now();
}

/**
 * Pro portal entitlement: **only** Stripe `active` or `trialing`, and within current period when end is set.
 * `canceled` (even with a future `current_period_end` in the DB) is **not** Pro — billing dates are informational only.
 */
export function isActiveSubscription(row: SubscriptionRow | null): boolean {
  if (!row) return false;
  if (row.status !== "active" && row.status !== "trialing") return false;

  if (!row.current_period_end) return true;
  const end = new Date(row.current_period_end).getTime();
  return Number.isFinite(end) ? end > Date.now() : false;
}

/** `past_due`: keep limited portal grace until period end (payment recovery). */
export function isPastDueWithGrace(row: SubscriptionRow | null): boolean {
  if (!row || row.status !== "past_due") return false;
  return subscriptionPeriodStillOpen(row);
}

/** Stripe subscription can still be canceled from our portal (live subscription). */
export function canCancelStripeSubscription(row: SubscriptionRow | null): boolean {
  if (!row?.stripe_subscription_id) return false;
  const s = row.status;
  return s === "active" || s === "trialing" || s === "past_due";
}

/** Download, license, and Pro badge — active/trial subscription, or past_due still inside the paid period. */
export function canUseProFeatures(row: SubscriptionRow | null): boolean {
  return isActiveSubscription(row) || isPastDueWithGrace(row);
}
