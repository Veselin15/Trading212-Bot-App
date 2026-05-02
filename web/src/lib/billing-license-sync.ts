import type { SupabaseClient } from "@supabase/supabase-js";

/** Admin / service-role Supabase client (bypasses RLS). */
export type AdminClient = SupabaseClient;

export async function getUserIdForStripeCustomer(
  admin: AdminClient,
  stripeCustomerId: string,
): Promise<string | null> {
  const { data, error } = await admin
    .from("subscriptions")
    .select("user_id")
    .eq("stripe_customer_id", stripeCustomerId)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (error) return null;
  const uid = data?.user_id;
  return typeof uid === "string" ? uid : null;
}

/**
 * After a Stripe subscription webhook, decide license rows.
 * `canceled` / terminal → revoke immediately (portal must not treat canceled as Pro).
 */
export function licenseEffectFromSubscriptionRow(
  status: string,
  _currentPeriodEndIso: string | null,
): "ensure" | "revoke" | "ignore" {
  const s = status.toLowerCase();
  if (s === "active" || s === "trialing") return "ensure";
  if (s === "past_due") return "ignore";
  if (
    s === "canceled" ||
    s === "unpaid" ||
    s === "incomplete_expired" ||
    s === "incomplete" ||
    s === "paused"
  ) {
    return "revoke";
  }
  return "ignore";
}

export async function ensureSubscriberLicense(admin: AdminClient, userId: string): Promise<void> {
  const { data: row } = await admin
    .from("licenses")
    .select("id")
    .eq("user_id", userId)
    .eq("status", "active")
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (row) return;

  await admin.from("licenses").insert({ user_id: userId, status: "active" });
}

export async function revokeActiveSubscriberLicenses(admin: AdminClient, userId: string): Promise<void> {
  const now = new Date().toISOString();
  await admin
    .from("licenses")
    .update({ status: "revoked", revoked_at: now })
    .eq("user_id", userId)
    .eq("status", "active");
}

export async function applyLicenseEffectForStripeCustomer(
  admin: AdminClient,
  stripeCustomerId: string,
  effect: "ensure" | "revoke" | "ignore",
): Promise<void> {
  if (effect === "ignore") return;
  const userId = await getUserIdForStripeCustomer(admin, stripeCustomerId);
  if (!userId) return;
  if (effect === "ensure") await ensureSubscriberLicense(admin, userId);
  else await revokeActiveSubscriberLicenses(admin, userId);
}

/** Revoke active licenses if DB subscription row is terminal (e.g. user loads dashboard after cancel). */
export async function revokeLicensesIfSubscriptionTerminal(
  admin: AdminClient,
  userId: string,
  status: string,
): Promise<void> {
  const s = status.toLowerCase();
  if (s === "canceled" || s === "unpaid" || s === "incomplete_expired" || s === "incomplete" || s === "paused") {
    await revokeActiveSubscriberLicenses(admin, userId);
  }
}
