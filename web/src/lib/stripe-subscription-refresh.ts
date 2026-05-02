import Stripe from "stripe";

import { revokeLicensesIfSubscriptionTerminal } from "@/lib/billing-license-sync";
import { getStripeClient } from "@/lib/stripe";
import { getStripeSubscriptionPeriodEndUnix } from "@/lib/stripe-subscription-period";
import { createSupabaseAdminClient } from "@/lib/supabase/admin";

type SubRow = { id: string; stripe_subscription_id: string | null };

/**
 * Pulls the latest period end + status from Stripe into `public.subscriptions`.
 * Fixes rows that missed `current_period_end` from webhooks (e.g. only invoice events received).
 */
export async function refreshSubscriptionRowFromStripe(userId: string): Promise<void> {
  if (!process.env.STRIPE_SECRET_KEY) return;

  const admin = createSupabaseAdminClient();

  const { data: withSub } = await admin
    .from("subscriptions")
    .select("id, stripe_subscription_id")
    .eq("user_id", userId)
    .not("stripe_subscription_id", "is", null)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  let row = withSub as SubRow | null;
  if (!row?.id || !row.stripe_subscription_id) {
    const { data: anyRow } = await admin
      .from("subscriptions")
      .select("id, stripe_subscription_id")
      .eq("user_id", userId)
      .order("created_at", { ascending: false })
      .limit(1)
      .maybeSingle();
    row = anyRow as SubRow | null;
  }

  if (!row?.id) return;
  const subId = row.stripe_subscription_id;
  if (!subId || typeof subId !== "string") return;

  let sub: Stripe.Subscription;
  try {
    sub = await getStripeClient().subscriptions.retrieve(subId, {
      expand: ["items.data.price"],
    });
  } catch {
    return;
  }

  const unix = getStripeSubscriptionPeriodEndUnix(sub);
  const current_period_end = unix != null ? new Date(unix * 1000).toISOString() : null;

  const raw = sub.status;
  const status = raw === "active" ? "active" : raw;

  await admin
    .from("subscriptions")
    .update({
      current_period_end: current_period_end,
      status,
      stripe_subscription_id: sub.id,
    })
    .eq("id", row.id);

  await revokeLicensesIfSubscriptionTerminal(admin, userId, status);
}
