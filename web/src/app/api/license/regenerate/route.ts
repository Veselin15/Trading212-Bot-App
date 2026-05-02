import { NextResponse } from "next/server";

import { type SubscriptionRow, canUseProFeatures } from "@/lib/subscription-model";
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

  // Only allow license regeneration for active subscribers.
  const { data: subRow } = await supabase
    .from("subscriptions")
    .select("status,current_period_end,stripe_customer_id,stripe_subscription_id")
    .eq("user_id", userRes.user.id)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  const sub = (subRow as SubscriptionRow | null) ?? null;
  if (sub?.status === "canceled") {
    return NextResponse.json({ error: "Subscription canceled — license cannot be issued or rotated." }, { status: 403 });
  }
  if (!canUseProFeatures(sub)) {
    return NextResponse.json({ error: "Subscription not active" }, { status: 403 });
  }

  const admin = createSupabaseAdminClient();
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

  const site = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
  return NextResponse.redirect(new URL("/dashboard?license=regenerated", site), { status: 303 });
}

