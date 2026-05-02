import { NextResponse } from "next/server";

import { requiredEnv } from "@/lib/env";
import { getStripeClient } from "@/lib/stripe";
import { createSupabaseAdminClient } from "@/lib/supabase/admin";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export async function POST() {
  if (!process.env.STRIPE_SECRET_KEY || !process.env.STRIPE_PRICE_ID) {
    return NextResponse.json({ error: "Stripe not configured" }, { status: 503 });
  }

  const supabase = await createSupabaseServerClient();
  const { data: userRes, error: userErr } = await supabase.auth.getUser();
  if (userErr || !userRes.user) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

  const admin = createSupabaseAdminClient();
  const { data: existingSub, error: subErr } = await admin
    .from("subscriptions")
    .select("stripe_customer_id")
    .eq("user_id", userRes.user.id)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (subErr) {
    return NextResponse.json({ error: "Failed to read subscriptions" }, { status: 500 });
  }

  const stripe = getStripeClient();

  let customerId = existingSub?.stripe_customer_id ?? null;
  if (!customerId) {
    const customer = await stripe.customers.create({
      email: userRes.user.email ?? undefined,
      metadata: { supabase_user_id: userRes.user.id },
    });
    customerId = customer.id;

    // Create a placeholder subscription row so we retain customer mapping.
    await admin.from("subscriptions").insert({
      user_id: userRes.user.id,
      stripe_customer_id: customerId,
      status: "inactive",
    });
  }

  const session = await stripe.checkout.sessions.create({
    mode: "subscription",
    customer: customerId,
    client_reference_id: userRes.user.id,
    metadata: { supabase_user_id: userRes.user.id },
    line_items: [{ price: requiredEnv("STRIPE_PRICE_ID"), quantity: 1 }],
    allow_promotion_codes: true,
    success_url: `${siteUrl}/dashboard?checkout=success`,
    cancel_url: `${siteUrl}/dashboard?checkout=cancel`,
  });

  if (!session.url) {
    return NextResponse.json({ error: "Stripe session URL missing" }, { status: 500 });
  }

  return NextResponse.redirect(session.url, { status: 303 });
}

