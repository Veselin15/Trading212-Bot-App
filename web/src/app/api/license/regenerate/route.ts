import { NextResponse } from "next/server";

import { type SubscriptionRow } from "@/lib/subscription-model";
import { type ProfileRow, computeEffectiveTier, tierCanUseLicense } from "@/lib/tier";
import { ensureProfileForUser } from "@/lib/profile";
import { refreshSubscriptionRowFromStripe } from "@/lib/stripe-subscription-refresh";
import { createSupabaseAdminClient } from "@/lib/supabase/admin";
import { createSupabaseServerClient } from "@/lib/supabase/server";

function newKey(): string {
  // UUID format, fine for a "license_key" uuid column in Postgres.
  return crypto.randomUUID();
}

export async function POST() {
  const supabase = await createSupabaseServerClient();
  const { data: userRes, error: userErr } = await supabase.auth.getUser();
  if (userErr || !userRes.user) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  await refreshSubscriptionRowFromStripe(userRes.user.id, { email: userRes.user.email });

  const admin = createSupabaseAdminClient();
  await ensureProfileForUser(admin, userRes.user.id);

  const [{ data: subRow }, { data: profRow }] = await Promise.all([
    supabase
      .from("subscriptions")
      .select("status,current_period_end,stripe_customer_id,stripe_subscription_id,plan")
      .eq("user_id", userRes.user.id)
      .order("created_at", { ascending: false })
      .limit(1)
      .maybeSingle(),
    supabase.from("profiles").select("subscription_tier,trial_ends_at").eq("user_id", userRes.user.id).maybeSingle(),
  ]);

  const sub = (subRow as SubscriptionRow | null) ?? null;
  const profile = (profRow as ProfileRow | null) ?? null;
  const tier = computeEffectiveTier(sub, profile);

  // TRIAL and PRO may hold a license key; EXPIRED may not.
  if (!tierCanUseLicense(tier)) {
    return NextResponse.json(
      { error: "Your free trial has ended. Upgrade to issue a license key." },
      { status: 403 },
    );
  }
  const { data: existing } = await admin
    .from("licenses")
    .select("id")
    .eq("user_id", userRes.user.id)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  const license_key = newKey();

  if (existing?.id) {
    const { error } = await admin
      .from("licenses")
      .update({ license_key, status: "active", revoked_at: null })
      .eq("id", existing.id);
    if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  } else {
    const { error } = await admin
      .from("licenses")
      .insert({ user_id: userRes.user.id, license_key, status: "active" });
    if (error) return NextResponse.json({ error: error.message }, { status: 500 });
  }

  const site = process.env.NEXT_PUBLIC_SITE_URL || "https://swifttrade.app";
  return NextResponse.redirect(new URL("/dashboard?license=regenerated", site), { status: 303 });
}

