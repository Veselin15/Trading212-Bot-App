/** Server-only: whether Checkout can run for at least one plan (env present). */
export function isStripeCheckoutConfigured(): boolean {
  const hasPrice = Boolean(
    process.env.STRIPE_PRICE_ID_PRO || process.env.STRIPE_PRICE_ID || process.env.STRIPE_PRICE_ID_STARTER,
  );
  return Boolean(process.env.STRIPE_SECRET_KEY && hasPrice);
}

/** Server-only: Billing Portal session can be created. */
export function isStripePortalConfigured(): boolean {
  return Boolean(process.env.STRIPE_SECRET_KEY);
}
