import type { Metadata } from "next";
import { getMyProfile } from "@/lib/profile";
import { getMySubscription } from "@/lib/subscription";
import { computeEffectiveTier, type EffectiveTier } from "@/lib/tier";
import { isStripeCheckoutConfigured } from "@/lib/stripe-env";

import { PricingPageClient, type PricingCta } from "./PricingPageClient";

export const metadata: Metadata = {
  title: "Pricing — Trading212 Bot Plans",
  description:
    "14-day free trial, no card required. Starter from €19/mo for EU stock signals. Pro from €49/mo for full ML signal feed and live execution on Trading212.",
  keywords: [
    "Trading212 bot pricing",
    "EU stock trading bot cost",
    "Trading212 automation subscription",
    "automated trading EU price",
  ],
  alternates: { canonical: "/pricing" },
  openGraph: {
    title: "Pricing — Trading212 Bot Plans · SwiftTrade",
    description:
      "Starter €19/mo · Pro €49/mo · 14-day free trial. Automate your Trading212 EU stock portfolio.",
    url: "/pricing",
  },
};

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
