import { getMyProfile } from "@/lib/profile";
import { getMySubscription } from "@/lib/subscription";
import { computeEffectiveTier, type EffectiveTier } from "@/lib/tier";
import { isStripeCheckoutConfigured } from "@/lib/stripe-env";

import { PricingPageClient, type PricingCta } from "./PricingPageClient";

export default async function PricingPage() {
  let cta: PricingCta = {
    loggedIn: false,
    checkoutEnabled: false,
    currentTier: null,
  };

  const { user, subscription } = await getMySubscription();
  if (user) {
    const profile = await getMyProfile();
    const tier: EffectiveTier = computeEffectiveTier(subscription, profile);
    cta = {
      loggedIn: true,
      checkoutEnabled: isStripeCheckoutConfigured(),
      currentTier: tier,
    };
  }

  return <PricingPageClient cta={cta} />;
}
