import type Stripe from "stripe";

import type { AdminClient } from "@/lib/billing-license-sync";
import { getUserIdForStripeCustomer } from "@/lib/billing-license-sync";
import { planFromStripeSubscription } from "@/lib/plans";
import { getStripeSubscriptionPeriodEndUnix } from "@/lib/stripe-subscription-period";
import { getStripeClient } from "@/lib/stripe";

/** Resolve Supabase user id for a Stripe customer (DB row, then Stripe metadata). */
export async function resolveSupabaseUserIdForStripeCustomer(
  admin: AdminClient,
  stripeCustomerId: string,
  hintedUserId?: string | null,
): Promise<string | null> {
  if (hintedUserId) return hintedUserId;

  const fromDb = await getUserIdForStripeCustomer(admin, stripeCustomerId);
  if (fromDb) return fromDb;

  try {
    const customer = await getStripeClient().customers.retrieve(stripeCustomerId);
    if (customer.deleted) return null;
    const meta = customer.metadata?.supabase_user_id;
    return typeof meta === "string" && meta.length > 0 ? meta : null;
  } catch {
    return null;
  }
}

/** Find or create `public.subscriptions` row for a user before Stripe sync. */
export async function ensureSubscriptionRowForUser(
  admin: AdminClient,
  userId: string,
  email: string | null | undefined,
): Promise<{ id: string; stripe_customer_id: string | null; stripe_subscription_id: string | null } | null> {
  const { data: existing } = await admin
    .from("subscriptions")
    .select("id, stripe_customer_id, stripe_subscription_id")
    .eq("user_id", userId)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (existing?.id) {
    return existing as { id: string; stripe_customer_id: string | null; stripe_subscription_id: string | null };
  }

  if (!email) return null;

  const stripe = getStripeClient();
  const listed = await stripe.customers.list({ email, limit: 10 });
  const customer = listed.data.find((c) => c.metadata?.supabase_user_id === userId) ?? listed.data[0];
  if (!customer?.id) return null;

  const { data: inserted, error } = await admin
    .from("subscriptions")
    .insert({
      user_id: userId,
      stripe_customer_id: customer.id,
      status: "inactive",
    })
    .select("id, stripe_customer_id, stripe_subscription_id")
    .single();

  if (error || !inserted) return null;
  return inserted as { id: string; stripe_customer_id: string | null; stripe_subscription_id: string | null };
}

export function subscriptionPatchFromStripeSubscription(sub: Stripe.Subscription): Record<string, unknown> {
  const unix = getStripeSubscriptionPeriodEndUnix(sub);
  const current_period_end = unix != null ? new Date(unix * 1000).toISOString() : null;
  const raw = sub.status;
  const status = raw === "active" ? "active" : raw;

  return {
    stripe_subscription_id: sub.id,
    status,
    plan: planFromStripeSubscription(sub),
    ...(current_period_end ? { current_period_end } : {}),
  };
}
