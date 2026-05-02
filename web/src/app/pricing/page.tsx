import { createSupabaseServerClient } from "@/lib/supabase/server";
import { getMySubscription, canUseProFeatures } from "@/lib/subscription";
import { isStripeCheckoutConfigured } from "@/lib/stripe-env";

import { PricingPageClient, type ProTierCta } from "./PricingPageClient";

export default async function PricingPage() {
  const supabase = await createSupabaseServerClient();
  const { data } = await supabase.auth.getUser();

  let proTier: ProTierCta = {
    loggedIn: false,
    checkoutEnabled: false,
    subscriptionActive: false,
  };

  if (data.user) {
    const { subscription } = await getMySubscription();
    const subscriptionActive = canUseProFeatures(subscription);
    proTier = {
      loggedIn: true,
      checkoutEnabled: isStripeCheckoutConfigured() && !subscriptionActive,
      subscriptionActive,
    };
  }

  return <PricingPageClient proTier={proTier} />;
}
