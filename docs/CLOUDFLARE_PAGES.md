# Cloudflare deployment (web portal — free tier)

The web app uses **@opennextjs/cloudflare** (not `@cloudflare/next-on-pages`) so Stripe webhooks and Supabase auth route handlers work on Cloudflare’s free Workers/Pages Git deploy.

Backend stays on your home server: `https://signals.swifttrade.app`

---

## 1) Push code to GitHub

Commit and push the `web/` OpenNext changes to `main`.

---

## 2) Create Cloudflare application (Git-connected)

1. Cloudflare Dashboard → **Workers & Pages**
2. **Create application** → **Pages** (or Workers with Git — same build UI)
3. **Connect to Git** → select `Veselin15/Trading212-Bot-App`
4. If repo not listed: GitHub → **Settings → Applications → Installed GitHub Apps → Cloudflare Pages → Configure** → allow this private repo.

### Build settings (strict)

| Setting | Value |
|---------|--------|
| **Root directory** | `web` |
| **Framework preset** | None |
| **Build command** | `npm ci && npm run pages:build` |
| **Build output directory** | *(leave empty)* |
| **Deploy command** (if shown) | `npx opennextjs-cloudflare deploy` |

If there is **no Deploy command** field, use:

| Build command |
|---------------|
| `npm ci && npm run pages:deploy` |

**Do not** use `npm run build` alone — that skips the OpenNext adapter step.

---

## 3) Environment variables (before first deploy)

In the Cloudflare project → **Settings → Environment variables** (Production):

| Variable | Example |
|----------|---------|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://xxx.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | service role (secret) |
| `STRIPE_SECRET_KEY` | `sk_test_...` first |
| `STRIPE_PRICE_ID` | `price_...` |
| `NEXT_PUBLIC_SITE_URL` | `https://swifttrade.app` |
| `STRIPE_CUSTOMER_PORTAL_RETURN_URL` | `https://swifttrade.app/dashboard` |
| `DESKTOP_SIGNAL_SERVER_URL` | `wss://signals.swifttrade.app/ws/exec` |
| `DESKTOP_APP_VERSION` | `1.0.0` |
| `DESKTOP_DOWNLOAD_URL` | GitHub release URL (placeholder OK until EXE ships) |

Add `STRIPE_WEBHOOK_SECRET` **after** creating the Stripe webhook (Step 5).

Save → **Redeploy**.

---

## 4) Custom domain

Project → **Custom domains** → add `swifttrade.app` (and optional `www`).

DNS stays on Cloudflare; the app assigns records automatically when the domain is on the same account.

---

## 5) Stripe webhook

1. Stripe (test mode) → **Developers → Webhooks → Add endpoint**
2. URL: `https://swifttrade.app/api/stripe/webhook`
3. Events: `checkout.session.completed`, `customer.subscription.*`, `invoice.payment_failed`, `invoice.payment_succeeded`, `invoice.paid`
4. Copy signing secret → Cloudflare env `STRIPE_WEBHOOK_SECRET` → redeploy

---

## 6) Verify

- [ ] `https://swifttrade.app` loads
- [ ] Sign up / login works (Supabase)
- [ ] Subscribe with test card `4242…` → dashboard shows license key
- [ ] Stripe webhook deliveries show **200**

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Build fails on middleware/proxy | Repo uses `src/middleware.ts` for OpenNext (not `proxy.ts`) |
| `NEXT_PUBLIC_*` missing at runtime | Set env vars in Cloudflare **before** build; redeploy |
| Webhook 400 | Wrong `STRIPE_WEBHOOK_SECRET`; update and redeploy |
| Build works locally but not on CF | Ensure root directory is `web` |

Local preview (optional):

```bash
cd web
npm ci
npm run pages:preview
```
