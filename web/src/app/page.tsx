import { HomeClient, type HomeCtaMode } from "./HomeClient";
import { getMySubscription, canUseProFeatures } from "@/lib/subscription";
import { isStripeCheckoutConfigured } from "@/lib/stripe-env";
import { getServerUser } from "@/lib/supabase/server";

const APP_JSONLD = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "SwiftTrade",
  applicationCategory: "FinanceApplication",
  operatingSystem: "Windows",
  description:
    "Automated Trading212 bot for EU stocks. ML ensemble signals delivered in real time; your API keys never leave your PC. Long-only EU equity strategy with 14-day free trial.",
  url: "https://swifttrade.app",
  offers: [
    {
      "@type": "Offer",
      name: "Starter",
      price: "19.00",
      priceCurrency: "EUR",
      priceSpecification: { "@type": "UnitPriceSpecification", billingDuration: "P1M" },
    },
    {
      "@type": "Offer",
      name: "Pro",
      price: "49.00",
      priceCurrency: "EUR",
      priceSpecification: { "@type": "UnitPriceSpecification", billingDuration: "P1M" },
    },
  ],
  featureList: [
    "Trading212 automation",
    "EU stock signals",
    "ML ensemble strategy",
    "API keys stay local",
    "Paper trading mode",
    "Supabase Realtime signal delivery",
  ],
};

export default async function Home() {
  const user = await getServerUser();

  let ctaMode: HomeCtaMode = { kind: "visitor" };
  if (user) {
    const { subscription } = await getMySubscription();
    ctaMode = {
      kind: "member",
      hasPro: canUseProFeatures(subscription),
      checkoutEnabled: isStripeCheckoutConfigured(),
    };
  }

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(APP_JSONLD) }}
      />
      <HomeClient ctaMode={ctaMode} />
    </>
  );
}
