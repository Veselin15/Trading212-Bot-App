import { NextResponse } from "next/server";

import Stripe from "stripe";

import { requiredEnv } from "@/lib/env";
import { getStripeClient } from "@/lib/stripe";
import { createSupabaseAdminClient } from "@/lib/supabase/admin";

export async function POST(request: Request) {
  const stripe = getStripeClient();
  const sig = request.headers.get("stripe-signature");
  if (!sig) return NextResponse.json({ error: "Missing Stripe-Signature" }, { status: 400 });

  const rawBody = await request.text();

  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(rawBody, sig, requiredEnv("STRIPE_WEBHOOK_SECRET"));
  } catch (err) {
    return NextResponse.json({ error: `Invalid signature: ${String(err)}` }, { status: 400 });
  }

  const admin = createSupabaseAdminClient();

  async function upsertByCustomer(customerId: string, patch: Record<string, unknown>) {
    // Ensure we have a row; if it doesn't exist, insert a new one with no user_id mapping yet.
    // (In practice, checkout route creates a placeholder row mapped to user_id.)
    const { data: existing } = await admin
      .from("subscriptions")
      .select("id,user_id,stripe_customer_id")
      .eq("stripe_customer_id", customerId)
      .order("created_at", { ascending: false })
      .limit(1)
      .maybeSingle();

    if (existing?.id) {
      await admin.from("subscriptions").update(patch).eq("id", existing.id);
      return;
    }

    await admin.from("subscriptions").insert({ stripe_customer_id: customerId, status: "inactive", ...patch });
  }

  try {
    switch (event.type) {
      case "checkout.session.completed": {
        const session = event.data.object as Stripe.Checkout.Session;
        const customer = session.customer;
        if (typeof customer !== "string") break;

        // When checkout completes, Stripe subscription may be created; we still mark active best-effort here.
        await upsertByCustomer(customer, {
          status: "active",
        });
        break;
      }

      case "customer.subscription.created":
      case "customer.subscription.updated":
      case "customer.subscription.deleted": {
        const sub = event.data.object as Stripe.Subscription;
        const customerId = typeof sub.customer === "string" ? sub.customer : "";
        if (!customerId) break;

        const status = String(sub.status || "inactive");
        const currentPeriodEndUnix = (sub as unknown as { current_period_end?: number }).current_period_end;
        const currentPeriodEnd = currentPeriodEndUnix ? new Date(currentPeriodEndUnix * 1000).toISOString() : null;

        await upsertByCustomer(customerId, {
          stripe_subscription_id: sub.id,
          status: status === "active" ? "active" : status,
          current_period_end: currentPeriodEnd,
        });
        break;
      }

      case "invoice.payment_failed": {
        const invoice = event.data.object as Stripe.Invoice;
        const customerId = typeof invoice.customer === "string" ? invoice.customer : "";
        if (!customerId) break;
        await upsertByCustomer(customerId, { status: "past_due" });
        break;
      }

      case "invoice.payment_succeeded": {
        const invoice = event.data.object as Stripe.Invoice;
        const customerId = typeof invoice.customer === "string" ? invoice.customer : "";
        if (!customerId) break;
        await upsertByCustomer(customerId, { status: "active" });
        break;
      }

      default:
        break;
    }
  } catch (err) {
    return NextResponse.json({ error: `Webhook handler error: ${String(err)}` }, { status: 500 });
  }

  // Return 200 so Stripe doesn't retry.
  return NextResponse.json({ ok: true });
}

