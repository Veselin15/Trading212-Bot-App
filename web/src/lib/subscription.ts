import { cache } from "react";

import { createSupabaseServerClient, getServerUser } from "@/lib/supabase/server";

import { type SubscriptionRow } from "@/lib/subscription-model";

export type { SubscriptionRow } from "@/lib/subscription-model";
export {
  canCancelStripeSubscription,
  canUseProFeatures,
  isActiveSubscription,
  isPastDueWithGrace,
  subscriptionPeriodStillOpen,
} from "@/lib/subscription-model";

/**
 * The signed-in user's latest subscription row. Memoized per-request so the header
 * and the page share one DB read (and one validated `getUser()` via `getServerUser`).
 */
export const getMySubscription = cache(async () => {
  const user = await getServerUser();
  if (!user) return { user: null, subscription: null };

  const supabase = await createSupabaseServerClient();
  const { data } = await supabase
    .from("subscriptions")
    .select("status,current_period_end,stripe_customer_id,stripe_subscription_id,plan")
    .eq("user_id", user.id)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  return { user, subscription: (data as SubscriptionRow | null) ?? null };
});
