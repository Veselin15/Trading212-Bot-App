#!/usr/bin/env sh
# Forward Stripe test webhooks to the local Next.js portal (port 3000).
# Only needed while testing checkout — not required for normal dev.
#
# Usage (from repo root):
#   ./scripts/stripe-webhooks.sh

set -eu

repo_root="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
env_file="$repo_root/web/.env.local"
forward_url="localhost:3000/api/stripe/webhook"
events="checkout.session.completed,customer.subscription.created,customer.subscription.updated,customer.subscription.deleted,invoice.payment_failed,invoice.payment_succeeded,invoice.paid"

if [ ! -f "$env_file" ] || ! grep -qE '^[[:space:]]*STRIPE_SECRET_KEY[[:space:]]*=[[:space:]]*[^[:space:]]' "$env_file"; then
  echo "ERROR: STRIPE_SECRET_KEY is missing in web/.env.local" >&2
  exit 1
fi

echo ""
echo "Stripe webhook forwarding (local dev only)"
echo "  1. Keep this terminal open while testing checkout."
echo "  2. Run the web portal elsewhere: cd web && npm run dev"
echo "  3. Copy whsec_... into web/.env.local as STRIPE_WEBHOOK_SECRET, then restart npm run dev."
echo ""
echo "Without this, reload /dashboard after checkout — subscription syncs from Stripe API."
echo ""

cd "$repo_root"

if command -v docker >/dev/null 2>&1; then
  echo "Starting Stripe CLI via Docker (profile: stripe)..."
  exec docker compose --profile stripe up stripe-cli
fi

if command -v stripe >/dev/null 2>&1; then
  echo "Docker not found — using native Stripe CLI..."
  exec stripe listen --forward-to "$forward_url" --events "$events"
fi

echo "ERROR: Install Docker or Stripe CLI (https://stripe.com/docs/stripe-cli)" >&2
exit 1
