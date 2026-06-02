import { NextResponse } from "next/server";

import Stripe from "stripe";

import {
  applyLicenseEffectForStripeCustomer,
  licenseEffectFromSubscriptionRow,
} from "@/lib/billing-license-sync";
import {
  resolveSupabaseUserIdForStripeCustomer,
  subscriptionPatchFromStripeSubscription,
} from "@/lib/stripe-customer-user";
import { applyProfileTierForStripeCustomer } from "@/lib/profile";
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

  async function upsertByCustomer(
    customerId: string,
    patch: Record<string, unknown>,
    insertUserId?: string | null,
  ) {
    const userId = await resolveSupabaseUserIdForStripeCustomer(admin, customerId, insertUserId);

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

    if (!userId) return;

    await admin.from("subscriptions").insert({
      user_id: userId,
      stripe_customer_id: customerId,
      status: "inactive",
      ...patch,
    });
  }

  try {
    switch (event.type) {
      case "checkout.session.completed": {
        const session = event.data.object as Stripe.Checkout.Session;
        const customer = session.customer;
        if (typeof customer !== "string") break;

        const metaUid =
          typeof session.metadata?.supabase_user_id === "string" && session.metadata.supabase_user_id.length > 0
            ? session.metadata.supabase_user_id
            : typeof session.client_reference_id === "string" && session.client_reference_id.length > 0
              ? session.client_reference_id
              : null;

        let patch: Record<string, unknown> = { status: "active" };

        let subId: string | undefined;
        if (typeof session.subscription === "string") {
          subId = session.subscription;
        } else if (
          session.subscription &&
          typeof session.subscription === "object" &&
          "id" in session.subscription
        ) {
          subId = (session.subscription as { id: string }).id;
        }

        if (subId) {
          const sub = await stripe.subscriptions.retrieve(subId, { expand: ["items.data.price"] });
          patch = subscriptionPatchFromStripeSubscription(sub);
        }

        await upsertByCustomer(customer, patch, metaUid);
        await applyLicenseEffectForStripeCustomer(admin, customer, "ensure");
        await applyProfileTierForStripeCustomer(admin, customer, String(patch.status ?? "active"));
        break;
      }

      case "customer.subscription.created":
      case "customer.subscription.updated":
      case "customer.subscription.deleted": {
        const sub = event.data.object as Stripe.Subscription;
        const customerId = typeof sub.customer === "string" ? sub.customer : "";
        if (!customerId) break;

        const patch = subscriptionPatchFromStripeSubscription(sub);
        const currentPeriodEnd =
          typeof patch.current_period_end === "string" ? patch.current_period_end : null;

        await upsertByCustomer(customerId, patch);

        const effect = licenseEffectFromSubscriptionRow(String(sub.status || "inactive"), currentPeriodEnd);
        await applyLicenseEffectForStripeCustomer(admin, customerId, effect);
        await applyProfileTierForStripeCustomer(admin, customerId, String(sub.status || "inactive"));
        break;
      }

      case "invoice.payment_failed": {
        const invoice = event.data.object as Stripe.Invoice;
        const customerId = typeof invoice.customer === "string" ? invoice.customer : "";
        if (!customerId) break;
        await upsertByCustomer(customerId, { status: "past_due" });
        await applyLicenseEffectForStripeCustomer(admin, customerId, "revoke");
        break;
      }

      case "invoice.payment_succeeded":
      case "invoice.paid": {
        const invoice = event.data.object as Stripe.Invoice;
        const customerId = typeof invoice.customer === "string" ? invoice.customer : "";
        if (!customerId) break;

        const linePeriod = invoice.lines?.data?.[0]?.period;
        const lineEnd = linePeriod && typeof linePeriod.end === "number" ? linePeriod.end : null;
        const invEnd = typeof invoice.period_end === "number" ? invoice.period_end : null;
        const periodUnix = lineEnd ?? invEnd;
        const current_period_end =
          periodUnix != null && Number.isFinite(periodUnix) && periodUnix > 0
            ? new Date(periodUnix * 1000).toISOString()
            : null;

        await upsertByCustomer(customerId, {
          status: "active",
          ...(current_period_end ? { current_period_end } : {}),
        });
        await applyLicenseEffectForStripeCustomer(admin, customerId, "ensure");
        await applyProfileTierForStripeCustomer(admin, customerId, "active");
        break;
      }

      default:
        break;
    }
  } catch (err) {
    return NextResponse.json({ error: `Webhook handler error: ${String(err)}` }, { status: 500 });
  }

  return NextResponse.json({ ok: true });
}
