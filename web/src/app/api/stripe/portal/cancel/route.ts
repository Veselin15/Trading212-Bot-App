import { NextResponse } from "next/server";

import { getStripeClient } from "@/lib/stripe";
import { createSupabaseAdminClient } from "@/lib/supabase/admin";
import { createSupabaseServerClient } from "@/lib/supabase/server";

/**
 * Opens Stripe Customer Portal directly on the subscription cancellation flow.
 */
export async function POST() {
  if (!process.env.STRIPE_SECRET_KEY) {
    return NextResponse.json({ error: "Stripe not configured" }, { status: 503 });
  }

  const supabase = await createSupabaseServerClient();
  const { data: userRes, error: userErr } = await supabase.auth.getUser();
  if (userErr || !userRes.user) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  const admin = createSupabaseAdminClient();
  const { data: sub, error: subErr } = await admin
    .from("subscriptions")
    .select("stripe_customer_id,stripe_subscription_id")
    .eq("user_id", userRes.user.id)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (subErr || !sub?.stripe_customer_id) {
    return NextResponse.json({ error: "No Stripe customer found" }, { status: 400 });
  }

  if (!sub.stripe_subscription_id || typeof sub.stripe_subscription_id !== "string") {
    return NextResponse.json(
      { error: "No subscription on file yet. Use Manage billing, or wait a moment after checkout." },
      { status: 400 },
    );
  }

  const stripe = getStripeClient();
  const returnUrl =
    process.env.STRIPE_CUSTOMER_PORTAL_RETURN_URL ||
    `${process.env.NEXT_PUBLIC_SITE_URL || "https://swifttrade.app"}/dashboard`;

  const session = await stripe.billingPortal.sessions.create({
    customer: sub.stripe_customer_id,
    return_url: returnUrl,
    flow_data: {
      type: "subscription_cancel",
      subscription_cancel: { subscription: sub.stripe_subscription_id },
    },
  });

  if (!session.url) {
    return NextResponse.json({ error: "Portal session URL missing" }, { status: 500 });
  }

  return NextResponse.redirect(session.url, { status: 303 });
}
