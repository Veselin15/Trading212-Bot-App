import { HomeClient, type HomeCtaMode } from "./HomeClient";
import { getMySubscription, canUseProFeatures } from "@/lib/subscription";
import { isStripeCheckoutConfigured } from "@/lib/stripe-env";
import { getServerUser } from "@/lib/supabase/server";

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

  return <HomeClient ctaMode={ctaMode} />;
}
