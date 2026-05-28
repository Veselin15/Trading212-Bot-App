# Web portal environment variables

Accounts and billing live in **Supabase** (`auth.users`, `public.subscriptions`, `public.licenses`). See [`supabase/README.md`](../supabase/README.md). Local Docker Postgres is for the Python backend only.

## Required (Supabase)

- `NEXT_PUBLIC_SUPABASE_URL` 
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## Required (Stripe)

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_ID` (the recurring subscription price id)

## Required (Supabase service role, server-only)

- `SUPABASE_SERVICE_ROLE_KEY` 

## Optional

- `NEXT_PUBLIC_SITE_URL` (default `https://swifttrade.app`; use `http://localhost:3000` for local dev)
- `STRIPE_CUSTOMER_PORTAL_RETURN_URL` (default `${NEXT_PUBLIC_SITE_URL}/dashboard`)
- `DESKTOP_DOWNLOAD_URL` (link to installer, e.g. GitHub Releases asset URL)
- `DESKTOP_APP_VERSION` (display-only version string shown on /download, e.g. `1.0.0`)
- `DESKTOP_CHANGELOG_URL` (optional link to release notes)
- `DESKTOP_SIGNAL_SERVER_URL` (display-only — the wss:// address baked into the EXE, shown on /download so users know which server their app connects to)

## Stripe webhooks

### Production (deployed site)

1. In [Stripe Dashboard → Webhooks](https://dashboard.stripe.com/webhooks), add endpoint:
   `https://<your-domain>/api/stripe/webhook`
2. Subscribe to: `checkout.session.completed`, `customer.subscription.*`, `invoice.payment_failed`, `invoice.payment_succeeded`, `invoice.paid`
3. Put the endpoint **signing secret** (`whsec_...`) in `STRIPE_WEBHOOK_SECRET` on the server.
4. Do **not** run `stripe listen` in production.

### Local development

Stripe cannot reach `localhost` directly. You have three options:

| Option | When to use |
|--------|-------------|
| **A. Docker Stripe CLI** (recommended) | Testing checkout with instant webhook updates |
| **B. No tunnel** | Casual dev — reload `/dashboard` after pay (syncs from Stripe API) |
| **C. Native Stripe CLI** | Same as A if you prefer a global `stripe` install |

**Option A — only while testing billing** (not required for normal dev):

```bash
# Terminal 1 — web portal
cd web && npm run dev

# Terminal 2 — webhook tunnel (repo root or web/)
docker compose --profile stripe up stripe-cli
# or from web/:  npm run stripe:listen
```

Copy the `whsec_...` line from the CLI output into `web/.env.local` as `STRIPE_WEBHOOK_SECRET`, then restart `npm run dev`.

The signing secret changes when you restart `stripe listen`; update `.env.local` if webhooks return 400.

**Option B** — skip the tunnel. After checkout, open or reload `/dashboard`; the app pulls subscription state from Stripe.

**Option C** — if Docker is unavailable:

```bash
stripe listen --forward-to localhost:3000/api/stripe/webhook
```

Or run `scripts/stripe-webhooks.ps1` / `scripts/stripe-webhooks.sh` (uses Docker when available, otherwise native CLI).
