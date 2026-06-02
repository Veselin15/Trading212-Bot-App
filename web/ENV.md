# Web portal environment variables

Accounts and billing live in **Supabase** (`auth.users`, `public.profiles`, `public.subscriptions`, `public.licenses`). See [`supabase/README.md`](../supabase/README.md). Local Docker Postgres is for the Python backend only.

## Tier model (TRIAL → PRO → EXPIRED)

A new account gets a **14-day free trial** (no card): the `handle_new_user` trigger creates a `public.profiles` row with `subscription_tier = 'TRIAL'` and `trial_ends_at = now() + 14 days`. The effective tier is computed at read time (`public.effective_tier`, mirrored in the web `lib/tier.ts` and the backend `resolve_license_tier`):

- **PRO** — active Stripe subscription on `STRIPE_PRICE_ID_PRO` (€49). Live execution on the **full** signal feed, up to 10 concurrent positions.
- **STARTER** — active Stripe subscription on `STRIPE_PRICE_ID_STARTER` (€19). Live execution on **core** signals only, up to 3 concurrent positions.
- **TRIAL** — inside the trial window. Full signal feed but paper trading only (2 positions).
- **EXPIRED** — trial ended (or subscription lapsed). Desktop app, signals, and license are locked until upgrade.

The price-id → plan mapping lives in `web/src/lib/plans.ts`; the webhook denormalizes the resolved plan into `subscriptions.plan`. The Starter↔Pro feature split is enforced server-side: the FastAPI backend tags each ML signal `min_tier` by confidence rank and the WebSocket layer withholds Pro-only signals from Starter connections.

There is **one paid tier**. Upgrading clears `trial_ends_at`, so a later cancellation drops the user to EXPIRED (not back into a stale trial).

## Required (Supabase)

- `NEXT_PUBLIC_SUPABASE_URL` 
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## Required (Stripe)

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_ID_STARTER` (€19/mo recurring price id)
- `STRIPE_PRICE_ID_PRO` (€49/mo recurring price id)
- `STRIPE_PRICE_ID` (legacy fallback — used as the Pro price if `STRIPE_PRICE_ID_PRO` is unset)

## Required (Supabase service role, server-only)

- `SUPABASE_SERVICE_ROLE_KEY` 

## Optional

- `NEXT_PUBLIC_SITE_URL` (default `https://swifttrade.app`; use `http://localhost:3000` for local dev)
- `STRIPE_CUSTOMER_PORTAL_RETURN_URL` (default `${NEXT_PUBLIC_SITE_URL}/dashboard`)
- `DESKTOP_DOWNLOAD_URL` (link to installer, e.g. GitHub Releases asset URL)
- `DESKTOP_DOWNLOAD_SHA256` (optional checksum shown on /download to help users verify integrity)
- `DESKTOP_APP_VERSION` (display-only version string shown on /download, e.g. `1.0.0`)
- `DESKTOP_CHANGELOG_URL` (optional link to release notes)
- `DESKTOP_SIGNAL_SERVER_URL` (display-only — the wss:// address baked into the EXE, shown on /download so users know which server their app connects to)
- `DESKTOP_VIRUSTOTAL_URL` (optional VirusTotal link shown on /download)

## Optional (trial email drip — Phase 5)

The drip is a **no-op** until these are set; nothing breaks without them.

- `RESEND_API_KEY` — Resend API key (verified sending domain required)
- `EMAIL_FROM` — e.g. `SwiftTrade <noreply@swifttrade.app>`
- `CRON_SECRET` — shared secret for the daily drip endpoint

`/api/cron/trial-emails` is **not** self-scheduling. Point a daily scheduler (Cloudflare Cron Trigger, Vercel Cron, or a GitHub Action) at it with header `x-cron-secret: <CRON_SECRET>`. It sends Day-7, Day-13, and post-expiry emails; the Day-1 welcome fires on signup. All sends are idempotent (one per stage per user, tracked on `public.profiles`).

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
