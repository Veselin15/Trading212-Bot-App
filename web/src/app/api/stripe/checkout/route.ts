import { NextResponse } from "next/server";

import type { PaidPlan } from "@/lib/subscription-model";
import { priceIdForPlan } from "@/lib/plans";
import { ensureStripeCustomerForUser, isStripeMissingResourceError } from "@/lib/stripe-customer-resolve";
import { getStripeClient } from "@/lib/stripe";
import { createSupabaseAdminClient } from "@/lib/supabase/admin";
import { createSupabaseServerClient } from "@/lib/supabase/server";

async function resolvePlan(request: Request): Promise<PaidPlan> {
  // Plan comes from the submitted form (`plan=starter|pro`); defaults to Pro.
  try {
    const form = await request.clone().formData();
    const raw = String(form.get("plan") ?? "").toLowerCase();
    if (raw === "starter") return "starter";
  } catch {
    // No form body (e.g. legacy callers) — fall through to Pro.
  }
  return "pro";
}

export async function POST(request: Request) {
  if (!process.env.STRIPE_SECRET_KEY) {
    return NextResponse.json({ error: "Stripe not configured" }, { status: 503 });
  }

  const plan = await resolvePlan(request);
  const priceId = priceIdForPlan(plan);
  if (!priceId) {
    return NextResponse.json({ error: `Stripe price for ${plan} plan not configured` }, { status: 503 });
  }

  const supabase = await createSupabaseServerClient();
  const { data: userRes, error: userErr } = await supabase.auth.getUser();
  if (userErr || !userRes.user) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  // Prefer request origin; env fallback prevents localhost redirects in production.
  const reqOrigin = new URL(request.url).origin;
  const envOrigin = (process.env.NEXT_PUBLIC_SITE_URL || "").trim();
  // If NEXT_PUBLIC_SITE_URL is accidentally left as localhost in production, ignore it.
  const envLooksLocal =
    envOrigin.startsWith("http://localhost") ||
    envOrigin.startsWith("https://localhost") ||
    envOrigin.includes("127.0.0.1");
  const siteUrl = (envOrigin && !envLooksLocal ? envOrigin : "") || reqOrigin || "https://swifttrade.app";

  const admin = createSupabaseAdminClient();
  const { data: existingSub, error: subErr } = await admin
    .from("subscriptions")
    .select("id,stripe_customer_id")
    .eq("user_id", userRes.user.id)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  if (subErr) {
    return NextResponse.json({ error: "Failed to read subscriptions" }, { status: 500 });
  }

  const stripe = getStripeClient();

  let subscriptionRowId = existingSub?.id ?? null;
  let customerId: string;
  try {
    if (subscriptionRowId) {
      customerId = await ensureStripeCustomerForUser(admin, {
        userId: userRes.user.id,
        email: userRes.user.email,
        existingCustomerId: existingSub?.stripe_customer_id,
        subscriptionRowId,
      });
    } else {
      customerId = await ensureStripeCustomerForUser(admin, {
        userId: userRes.user.id,
        email: userRes.user.email,
        existingCustomerId: null,
      });
      const { data: inserted, error: insertErr } = await admin
        .from("subscriptions")
        .insert({
          user_id: userRes.user.id,
          stripe_customer_id: customerId,
          status: "inactive",
        })
        .select("id")
        .single();
      if (insertErr || !inserted) {
        return NextResponse.json({ error: "Failed to save subscription row" }, { status: 500 });
      }
      subscriptionRowId = inserted.id;
    }
  } catch (err) {
    console.error("stripe checkout customer setup failed", err);
    return NextResponse.json({ error: "Stripe customer setup failed" }, { status: 502 });
  }

  let session;
  try {
    session = await stripe.checkout.sessions.create({
      mode: "subscription",
      customer: customerId,
      client_reference_id: userRes.user.id,
      metadata: { supabase_user_id: userRes.user.id, plan },
      line_items: [{ price: priceId, quantity: 1 }],
      allow_promotion_codes: true,
      success_url: `${siteUrl}/dashboard?checkout=success`,
      cancel_url: `${siteUrl}/dashboard?checkout=cancel`,
    });
  } catch (err) {
    console.error("stripe checkout session create failed", err);
    const hint = isStripeMissingResourceError(err)
      ? "Check STRIPE_PRICE_ID_STARTER / STRIPE_PRICE_ID_PRO are live-mode price ids."
      : "Stripe checkout failed.";
    return NextResponse.json({ error: hint }, { status: 502 });
  }

  if (!session.url) {
    return NextResponse.json({ error: "Stripe session URL missing" }, { status: 500 });
  }

  return NextResponse.redirect(session.url, { status: 303 });
}

