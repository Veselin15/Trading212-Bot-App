import { createSupabaseServerClient } from "@/lib/supabase/server";

export type SubscriptionRow = {
  status: string;
  current_period_end: string | null;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
};

export async function getMySubscription() {
  const supabase = await createSupabaseServerClient();

  const { data: userRes, error: userErr } = await supabase.auth.getUser();
  if (userErr || !userRes.user) return { user: null, subscription: null };

  const { data } = await supabase
    .from("subscriptions")
    .select("status,current_period_end,stripe_customer_id,stripe_subscription_id")
    .eq("user_id", userRes.user.id)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();

  return { user: userRes.user, subscription: (data as SubscriptionRow | null) ?? null };
}

export function isActiveSubscription(row: SubscriptionRow | null): boolean {
  if (!row) return false;
  if (row.status !== "active") return false;
  if (!row.current_period_end) return true;
  const end = new Date(row.current_period_end).getTime();
  return Number.isFinite(end) ? end > Date.now() : false;
}

