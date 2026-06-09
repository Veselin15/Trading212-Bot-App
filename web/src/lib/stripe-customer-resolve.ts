import type { AdminClient } from "@/lib/billing-license-sync";
import { getStripeClient } from "@/lib/stripe";

/** True when Stripe cannot find the customer/subscription (common after test → live migration). */
export function isStripeMissingResourceError(err: unknown): boolean {
  if (!err || typeof err !== "object") return false;
  const e = err as { type?: string; code?: string; statusCode?: number };
  return (
    (e.type === "StripeInvalidRequestError" && e.code === "resource_missing") || e.statusCode === 404
  );
}

/** Returns the customer id when it exists in the current Stripe mode; otherwise null. */
export async function resolveLiveStripeCustomerId(
  customerId: string | null | undefined,
): Promise<string | null> {
  if (!customerId) return null;

  const stripe = getStripeClient();
  try {
    const customer = await stripe.customers.retrieve(customerId);
    if (customer.deleted) return null;
    return customer.id;
  } catch (err) {
    if (isStripeMissingResourceError(err)) return null;
    throw err;
  }
}

/** Drop test-mode Stripe ids so live checkout can create a fresh customer. */
export async function clearStaleStripeBillingIds(admin: AdminClient, subscriptionRowId: string): Promise<void> {
  await admin
    .from("subscriptions")
    .update({
      stripe_customer_id: null,
      stripe_subscription_id: null,
      status: "inactive",
    })
    .eq("id", subscriptionRowId);
}

/**
 * Reuse a valid live customer id, or create one and persist it on the subscription row.
 * Clears stale test-mode ids automatically.
 */
export async function ensureStripeCustomerForUser(
  admin: AdminClient,
  args: {
    userId: string;
    email: string | null | undefined;
    existingCustomerId: string | null | undefined;
    subscriptionRowId?: string | null;
  },
): Promise<string> {
  const { userId, email, existingCustomerId, subscriptionRowId } = args;
  const valid = await resolveLiveStripeCustomerId(existingCustomerId);
  if (valid) return valid;

  if (subscriptionRowId && existingCustomerId) {
    await clearStaleStripeBillingIds(admin, subscriptionRowId);
  }

  const stripe = getStripeClient();
  const customer = await stripe.customers.create({
    email: email ?? undefined,
    metadata: { supabase_user_id: userId },
  });

  if (subscriptionRowId) {
    await admin
      .from("subscriptions")
      .update({ stripe_customer_id: customer.id, status: "inactive" })
      .eq("id", subscriptionRowId);
  }

  return customer.id;
}
