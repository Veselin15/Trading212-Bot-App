import type { AdminClient } from "@/lib/billing-license-sync";
import { getUserIdForStripeCustomer } from "@/lib/billing-license-sync";
import { type ProfileRow } from "@/lib/tier";
import { createSupabaseServerClient } from "@/lib/supabase/server";

const TRIAL_DAYS = 14;

function trialEndIso(days = TRIAL_DAYS): string {
  return new Date(Date.now() + days * 86_400_000).toISOString();
}

/** Read the signed-in user's profile row (RLS: own row only). */
export async function getMyProfile(): Promise<ProfileRow | null> {
  const supabase = await createSupabaseServerClient();
  const { data: userRes, error: userErr } = await supabase.auth.getUser();
  if (userErr || !userRes.user) return null;

  const { data } = await supabase
    .from("profiles")
    .select("subscription_tier,trial_ends_at")
    .eq("user_id", userRes.user.id)
    .maybeSingle();

  return (data as ProfileRow | null) ?? null;
}

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

/**
 * Set the denormalized tier hint. Upgrading to PRO clears `trial_ends_at` so a later
 * cancellation drops the user to EXPIRED (not back into a still-future trial window).
 */
export async function setProfileTier(
  admin: AdminClient,
  userId: string,
  tier: "PRO" | "EXPIRED",
): Promise<void> {
  const patch: Record<string, unknown> =
    tier === "PRO" ? { subscription_tier: "PRO", trial_ends_at: null } : { subscription_tier: "EXPIRED" };

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

/** Map a Stripe subscription status onto the profile tier hint, by Stripe customer. */
export async function applyProfileTierForStripeCustomer(
  admin: AdminClient,
  stripeCustomerId: string,
  status: string,
): Promise<void> {
  const s = status.toLowerCase();
  let tier: "PRO" | "EXPIRED" | null = null;
  if (s === "active" || s === "trialing") tier = "PRO";
  else if (["canceled", "unpaid", "incomplete_expired", "incomplete", "paused"].includes(s)) tier = "EXPIRED";
  // `past_due` is left untouched during the payment-recovery grace window.
  if (!tier) return;

  const userId = await getUserIdForStripeCustomer(admin, stripeCustomerId);
  if (!userId) return;
  await setProfileTier(admin, userId, tier);
}
