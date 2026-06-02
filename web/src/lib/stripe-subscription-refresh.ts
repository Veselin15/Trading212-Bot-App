import Stripe from "stripe";

import {
  ensureSubscriberLicense,
  revokeLicensesIfSubscriptionTerminal,
} from "@/lib/billing-license-sync";
import { planFromStripeSubscription } from "@/lib/plans";
import { setProfileTier } from "@/lib/profile";
import { getStripeClient } from "@/lib/stripe";
import {
  ensureSubscriptionRowForUser,
  subscriptionPatchFromStripeSubscription,
} from "@/lib/stripe-customer-user";
import { createSupabaseAdminClient } from "@/lib/supabase/admin";

type SubRow = {
  id: string;
  stripe_subscription_id: string | null;
  stripe_customer_id: string | null;
};

function pickStripeSubscription(subs: Stripe.Subscription[]): Stripe.Subscription | null {
  if (subs.length === 0) return null;
  return (
    subs.find((s) => s.status === "active" || s.status === "trialing") ??
    subs.find((s) => s.status !== "canceled" && s.status !== "incomplete_expired") ??
    subs[0] ??
    null
  );
}

async function resolveStripeSubscription(
  stripe: Stripe,
  row: SubRow,
): Promise<Stripe.Subscription | null> {
  if (row.stripe_subscription_id) {
    try {
      const direct = await stripe.subscriptions.retrieve(row.stripe_subscription_id, {
        expand: ["items.data.price"],
      });
      // If the stored subscription id is terminal, fall back to a customer lookup.
      // This happens after a user cancels and later re-subscribes: Stripe creates a new
      // subscription, but the DB may still point at the old canceled one.
      if (direct.status !== "canceled" && direct.status !== "incomplete_expired") {
        return direct;
      }
    } catch {
      // Fall through — subscription id may be stale; try customer lookup below.
    }
  }

  if (!row.stripe_customer_id) return null;

  const listed = await stripe.subscriptions.list({
    customer: row.stripe_customer_id,
    status: "all",
    limit: 10,
    expand: ["data.items.data.price"],
  });

  return pickStripeSubscription(listed.data);
}

export type RefreshSubscriptionOptions = {
  email?: string | null;
};

/**
 * Pulls the latest period end + status from Stripe into `public.subscriptions`.
 * Discovers subscriptions by Stripe customer when webhooks were missed (e.g. local dev).
 */
export async function refreshSubscriptionRowFromStripe(
  userId: string,
  options?: RefreshSubscriptionOptions,
): Promise<void> {
  if (!process.env.STRIPE_SECRET_KEY) return;

  const admin = createSupabaseAdminClient();
  const stripe = getStripeClient();

  let row = (await ensureSubscriptionRowForUser(admin, userId, options?.email)) as SubRow | null;

  if (!row?.id) {
    const { data: rowData } = await admin
      .from("subscriptions")
      .select("id, stripe_subscription_id, stripe_customer_id")
      .eq("user_id", userId)
      .order("created_at", { ascending: false })
      .limit(1)
      .maybeSingle();
    row = rowData as SubRow | null;
  }

  if (!row?.id) return;

  const sub = await resolveStripeSubscription(stripe, row);
  if (!sub) return;

  const patch = subscriptionPatchFromStripeSubscription(sub);

  await admin.from("subscriptions").update(patch).eq("id", row.id);

  const raw = sub.status;
  if (raw === "active" || raw === "trialing") {
    await ensureSubscriberLicense(admin, userId);
    await setProfileTier(admin, userId, planFromStripeSubscription(sub) === "starter" ? "STARTER" : "PRO");
  }

  await revokeLicensesIfSubscriptionTerminal(admin, userId, String(patch.status ?? raw));
  const finalStatus = String(patch.status ?? raw).toLowerCase();
  if (["canceled", "unpaid", "incomplete_expired", "incomplete", "paused"].includes(finalStatus)) {
    await setProfileTier(admin, userId, "EXPIRED");
  }
}
