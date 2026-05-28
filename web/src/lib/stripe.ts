import Stripe from "stripe";

import { requiredEnv } from "@/lib/env";

export function getStripeClient() {
  return new Stripe(requiredEnv("STRIPE_SECRET_KEY"), {
    apiVersion: "2026-04-22.dahlia",
    // Cloudflare Workers: force fetch-based HTTP client (Node http/tls is unreliable in the runtime).
    httpClient: Stripe.createFetchHttpClient(),
  });
}

