import { cache } from "react";

import type { AdminClient } from "@/lib/billing-license-sync";
import { getUserIdForStripeCustomer } from "@/lib/billing-license-sync";
import { type ProfileRow } from "@/lib/tier";
import { createSupabaseServerClient, getServerUser } from "@/lib/supabase/server";

const TRIAL_DAYS = 14;

function trialEndIso(days = TRIAL_DAYS): string {
  return new Date(Date.now() + days * 86_400_000).toISOString();
}

/** Read the signed-in user's profile row (RLS: own row only). Memoized per request. */
export const getMyProfile = cache(async (): Promise<ProfileRow | null> => {
  const user = await getServerUser();
  if (!user) return null;

  const supabase = await createSupabaseServerClient();
  const { data } = await supabase
    .from("profiles")
    .select("subscription_tier,trial_ends_at")
    .eq("user_id", user.id)
    .maybeSingle();

  return (data as ProfileRow | null) ?? null;
});

/**
 * Safety net for accounts created before the `handle_new_user` trigger / backfill:
 * create a TRIAL profile if one is missing. Never resets an existing row.
 */
export async function ensureProfileForUser(admin: AdminClient, userId: string): Promise<void> {
  const { data: existing } = await admin
    .from("profiles")
    .select("user_id")
    .eq("user_id", userId)
    .maybeSingle();
  if (existing) return;

  await admin
    .from("profiles")
    .insert({ user_id: userId, subscription_tier: "TRIAL", trial_ends_at: trialEndIso() });
}

export type ProfileTier = "STARTER" | "PRO" | "EXPIRED";

/**
 * Set the denormalized tier hint. Upgrading to a paid tier clears `trial_ends_at` so a
 * later cancellation drops the user to EXPIRED (not back into a still-future trial window).
 */
export async function setProfileTier(
  admin: AdminClient,
  userId: string,
  tier: ProfileTier,
): Promise<void> {
  const patch: Record<string, unknown> =
    tier === "EXPIRED" ? { subscription_tier: "EXPIRED" } : { subscription_tier: tier, trial_ends_at: null };

  const { data: existing } = await admin
    .from("profiles")
    .select("user_id")
    .eq("user_id", userId)
    .maybeSingle();

  if (existing) {
    await admin.from("profiles").update(patch).eq("user_id", userId);
  } else {
    await admin.from("profiles").insert({ user_id: userId, ...patch });
  }
}

/** Resolve the paid profile tier (STARTER/PRO) from the user's latest subscription plan. */
async function paidTierFromDbPlan(admin: AdminClient, userId: string): Promise<ProfileTier> {
  const { data } = await admin
    .from("subscriptions")
    .select("plan")
    .eq("user_id", userId)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();
  return data?.plan === "starter" ? "STARTER" : "PRO";
}

/**
 * Map a Stripe subscription status onto the profile tier hint, by Stripe customer.
 * For active/trialing the concrete tier (STARTER vs PRO) is read from the just-synced
 * `subscriptions.plan`, so this must run *after* the subscription row is updated.
 */
export async function applyProfileTierForStripeCustomer(
  admin: AdminClient,
  stripeCustomerId: string,
  status: string,
): Promise<void> {
  const s = status.toLowerCase();
  const userId = await getUserIdForStripeCustomer(admin, stripeCustomerId);
  if (!userId) return;

  if (s === "active" || s === "trialing") {
    await setProfileTier(admin, userId, await paidTierFromDbPlan(admin, userId));
  } else if (["canceled", "unpaid", "incomplete_expired", "incomplete", "paused"].includes(s)) {
    await setProfileTier(admin, userId, "EXPIRED");
  }
  // `past_due` is left untouched during the payment-recovery grace window.
}
