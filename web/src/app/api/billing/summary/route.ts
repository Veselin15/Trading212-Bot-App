import { NextResponse } from "next/server";

import { type SubscriptionRow, activePaidPlan, canUseProFeatures } from "@/lib/subscription-model";
import { createSupabaseServerClient } from "@/lib/supabase/server";

/**
 * JSON view of the signed-in user's subscription + whether an active license exists.
 * Used by the portal and for integration checks (no secrets returned).
 */
export async function GET() {
  const supabase = await createSupabaseServerClient();
  const { data: userRes, error: userErr } = await supabase.auth.getUser();
  if (userErr || !userRes.user) {
    return NextResponse.json({ error: "Not authenticated" }, { status: 401 });
  }

  const { data: sub } = await supabase
    .from("subscriptions")
    .select("status,current_period_end,stripe_customer_id,stripe_subscription_id,plan")
    .eq("user_id", userRes.user.id)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  const { data: lic } = await supabase
    .from("licenses")
    .select("status")
    .eq("user_id", userRes.user.id)
    .eq("status", "active")
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  const subscription = (sub as SubscriptionRow | null) ?? null;

  return NextResponse.json({
    subscription: subscription
      ? {
          status: subscription.status,
          current_period_end: subscription.current_period_end,
          has_stripe_customer: Boolean(subscription.stripe_customer_id),
          has_stripe_subscription: Boolean(subscription.stripe_subscription_id),
          is_active: canUseProFeatures(subscription),
          plan: activePaidPlan(subscription),
        }
      : null,
    license: {
      has_active: Boolean(lic),
    },
  });
}
