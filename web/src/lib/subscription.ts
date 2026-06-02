import { createSupabaseServerClient } from "@/lib/supabase/server";

import { type SubscriptionRow } from "@/lib/subscription-model";

export type { SubscriptionRow } from "@/lib/subscription-model";
export {
  canCancelStripeSubscription,
  canUseProFeatures,
  isActiveSubscription,
  isPastDueWithGrace,
  subscriptionPeriodStillOpen,
} from "@/lib/subscription-model";

export async function getMySubscription() {
  const supabase = await createSupabaseServerClient();

  const { data: userRes, error: userErr } = await supabase.auth.getUser();
  if (userErr || !userRes.user) return { user: null, subscription: null };

  const { data } = await supabase
    .from("subscriptions")
    .select("status,current_period_end,stripe_customer_id,stripe_subscription_id,plan")
    .eq("user_id", userRes.user.id)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  return { user: userRes.user, subscription: (data as SubscriptionRow | null) ?? null };
}
