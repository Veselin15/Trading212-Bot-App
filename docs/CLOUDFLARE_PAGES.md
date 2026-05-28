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

Use **two commands** if the UI has **Build command** and **Deploy command** (recommended):

| Setting | Value |
|---------|--------|
| **Root directory** | `web` |
| **Framework preset** | None |
| **Build command** | `npm ci && npm run pages:build` |
| **Deploy command** | `npx opennextjs-cloudflare deploy` |
| **Build output directory** | *(leave empty)* |

If you only have **one** command field, use:

| Build command |
|---------------|
| `npm ci && npm run pages:build` |

…and add **Build secrets** below (required for deploy in a single step).

**Do not** use `npm run pages:deploy` unless `CLOUDFLARE_API_TOKEN` is set (see Step 2b).

`web/wrangler.jsonc` **`name`** must match your Cloudflare project name (e.g. `trading212-bot-app`).

### Step 2b — Build secrets (required for deploy)

Cloudflare’s log error:

`CLOUDFLARE_API_TOKEN environment variable` … `necessary` … `non-interactive environment`

Fix:

1. Cloudflare Dashboard → **My Profile** → **API Tokens** → **Create Token**
2. Use template **“Edit Cloudflare Workers”** (or custom: Account + Workers Scripts Edit)
3. Copy the token once

4. Workers & Pages → **trading212-bot-app** → **Settings** → **Variables and Secrets** (or **Build** → **Environment variables**)
5. Add **Secrets** (encrypted):

| Name | Value |
|------|--------|
| `CLOUDFLARE_API_TOKEN` | token from step 3 |
| `CLOUDFLARE_ACCOUNT_ID` | your account ID (Dashboard URL or **Workers & Pages** overview) |

6. **Redeploy**

If using **one** build command field only:

| Build command |
|---------------|
| `npm ci && npm run pages:deploy` |

(with both secrets set above)

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
