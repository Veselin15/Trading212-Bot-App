/** Server-only: whether Checkout can run (env present). */
export function isStripeCheckoutConfigured(): boolean {
  return Boolean(process.env.STRIPE_SECRET_KEY && process.env.STRIPE_PRICE_ID);
}

/** Server-only: Billing Portal session can be created. */
export function isStripePortalConfigured(): boolean {
  return Boolean(process.env.STRIPE_SECRET_KEY);
}
