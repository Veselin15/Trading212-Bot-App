# SwiftTrade — strict deployment guide (end to end)

Follow **every step in order**. Do not skip verification checkpoints (✅).

**Target architecture**

| Piece | Where | Public URL |
|-------|--------|------------|
| Web portal | Cloudflare Pages | `https://swifttrade.app` |
| Signal backend | Docker on home server + Cloudflare Tunnel | `https://signals.swifttrade.app` |
| Desktop app | GitHub Releases (built on Windows) | Download from `/download` |

**Prerequisites (before Step 1)**

- [ ] GitHub repo with this code pushed to `main`
- [ ] Docker Hub account (e.g. `veski4a06`)
- [ ] Home server: Ubuntu, Docker, Watchtower, `cloudflared` tunnel already running
- [ ] Domain `swifttrade.app` on Cloudflare
- [ ] Windows PC with Python 3.12+ (for building `SwiftTrade.exe`)
- [ ] Accounts: Supabase, Stripe, Cloudflare, Docker Hub

---

## PART A — Database & auth (Supabase)

### Step 1 — Create Supabase project

1. Go to [https://supabase.com/dashboard](https://supabase.com/dashboard) → **New project**.
2. Choose region, set a strong database password, wait until status is **Active**.

✅ **Check:** Project dashboard loads.

### Step 2 — Run SQL migrations (exact order)

1. Open **SQL Editor** → **New query**.
2. Open repo file `supabase/migrations/20260428_000001_init_subscriptions_signals.sql` → copy all → **Run**.
3. Open `supabase/migrations/20260428_000002_init_licenses.sql` → copy all → **Run**.
4. Open `supabase/migrations/20260428_000003_add_license_enforcement_fields.sql` → copy all → **Run**.

✅ **Check:** **Table Editor** shows tables: `subscriptions`, `licenses`, `signals` (signals may stay empty — that is OK).

### Step 3 — Auth URL configuration

1. **Authentication** → **URL configuration**.
2. Set **Site URL** to: `https://swifttrade.app`
3. Under **Redirect URLs**, add exactly:
   - `https://swifttrade.app/auth/callback`
   - `http://localhost:3000/auth/callback` (for local dev only)
4. **Save**.

### Step 4 — Email provider (recommended for MVP)

1. **Authentication** → **Providers** → **Email**.
2. For fastest testing: disable **Confirm email** (you can enable later).
3. **Save**.

### Step 5 — Copy Supabase keys (store in a password manager)

1. **Project Settings** → **API**.
2. Copy and save these three values (you will paste them many times):

| Name | Where it goes |
|------|----------------|
| **Project URL** | `SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_URL` |
| **anon public** | `NEXT_PUBLIC_SUPABASE_ANON_KEY` |
| **service_role** (secret) | `SUPABASE_SERVICE_ROLE_KEY` |

⚠️ Never commit `service_role` to git or expose it in the browser.

✅ **Check:** You have three values saved locally.

---

## PART B — Billing (Stripe)

Do **test mode** first. Switch to live only after Part H passes.

### Step 6 — Create subscription product & price

1. [Stripe Dashboard](https://dashboard.stripe.com) → ensure **Test mode** is ON (toggle top-right).
2. **Product catalog** → **Add product** → name e.g. `SwiftTrade Pro`.
3. Add a **Recurring** price (monthly or yearly) → **Save**.
4. Open the **Price** → copy **Price ID** (`price_...`) → this is `STRIPE_PRICE_ID`.

✅ **Check:** `STRIPE_PRICE_ID` starts with `price_`.

### Step 7 — Copy Stripe secret key

1. **Developers** → **API keys**.
2. Copy **Secret key** (`sk_test_...`) → `STRIPE_SECRET_KEY`.

✅ **Check:** Key starts with `sk_test_` while in test mode.

### Step 8 — Stripe webhook (do AFTER web is live — Step 33)

Skip for now. You will create the webhook after `https://swifttrade.app` works.

---

## PART C — Build pipeline (GitHub → Docker Hub)

### Step 9 — Docker Hub access token

1. [hub.docker.com](https://hub.docker.com) → **Account Settings** → **Security** → **New Access Token**.
2. Name: `github-swifttrade`, permissions: **Read & Write**.
3. Copy token (shown once).

✅ **Check:** Token copied.

### Step 10 — GitHub repository secrets

1. GitHub repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.
2. Add **exactly**:

| Secret name | Value |
|-------------|--------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username (e.g. `veski4a06`) |
| `DOCKERHUB_TOKEN` | Token from Step 9 |

✅ **Check:** Two secrets listed under Actions.

### Step 11 — Push code to trigger backend image build

1. On your dev machine, ensure all deployment files are on `main`:
   - `.github/workflows/docker-backend.yml`
   - `backend/Dockerfile`
   - `deploy/*`
2. Push to `main` (or merge PR to `main`).

3. GitHub → **Actions** → workflow **Build and push backend image** → wait until green.

✅ **Check:** [hub.docker.com](https://hub.docker.com) → repository `veski4a06/swifttrade-backend` → tag `latest` exists.

> If the workflow does not run: push a small change under `backend/` or run workflow manually (**Actions** → workflow → **Run workflow**).

---

## PART D — Home server (signal backend)

SSH: `veski4a@192.168.0.104` (or your server user/host).

### Step 12 — Create deploy directory

```bash
mkdir -p ~/swifttrade/deploy
cd ~/swifttrade/deploy
```

### Step 13 — Copy compose file to the server

**Option A — from your PC (scp):**

```powershell
scp deploy/docker-compose.yml veski4a@192.168.0.104:~/swifttrade/deploy/docker-compose.yml
```

**Option B — on server, create file manually:** copy contents from repo `deploy/docker-compose.yml`.

✅ **Check:** `ls ~/swifttrade/deploy/docker-compose.yml` shows the file.

### Step 14 — Create `deploy/.env` on the server

```bash
cd ~/swifttrade/deploy
nano .env
```

Paste and **replace every placeholder**:

```env
SWIFTTRADE_BACKEND_IMAGE=veski4a06/swifttrade-backend:latest
BACKEND_HOST_PORT=8010

SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...your_service_role...

APP_BASE_URL=https://signals.swifttrade.app

RUN_DB_MIGRATIONS=false
DEBUG_ROUTES_ENABLED=false

JWT_SECRET=REPLACE_WITH_LONG_RANDOM_STRING
JWT_ISSUER=swifttrade-backend
JWT_AUDIENCE=swifttrade-portal
```

Save (`Ctrl+O`, Enter, `Ctrl+X`).

✅ **Check:** `grep SUPABASE_URL .env` shows your real URL, not `YOUR_PROJECT`.

### Step 15 — Pull and start backend container

```bash
cd ~/swifttrade/deploy
docker compose pull
docker compose up -d
docker compose ps
```

✅ **Check:** Container `swifttrade_backend` state is **running**.

### Step 16 — Local health checks (on server)

```bash
curl -s http://127.0.0.1:8010/health
curl -s http://127.0.0.1:8010/health/supabase-smoke
```

✅ **Check:**

- First command returns `"status":"ok"`.
- Second returns JSON with `resolved_url_len` and `resolved_key_len` **greater than 0**.

If `resolved_url_len` is 0: fix `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` in `.env` and run `docker compose up -d` again.

### Step 17 — Watchtower (auto-updates)

Confirm your existing Watchtower container monitors this backend (or all containers).

After you push new images to Docker Hub, within ~5 minutes the server should pull `swifttrade-backend:latest` and restart.

✅ **Check:** You know which Watchtower command/compose you use on this server.

---

## PART E — Cloudflare Tunnel (public backend)

### Step 18 — DNS hostname for API (if not automatic)

1. Cloudflare dashboard → domain **swifttrade.app** → **DNS**.
2. Ensure tunnel-created records exist for subdomains you will use (often created by Zero Trust when you add a public hostname).

### Step 19 — Add tunnel route for signal server

1. **Zero Trust** → **Networks** → **Tunnels** → select your tunnel → **Public Hostname** → **Add a public hostname**.
2. Set:
   - **Subdomain:** `signals`
   - **Domain:** `swifttrade.app`
   - **Type:** HTTP
   - **URL:** `localhost:8010`
3. **Save**.

✅ **Check:** Public hostname list shows `signals.swifttrade.app` → `http://localhost:8010`.

### Step 20 — Public health check (from any machine)

```bash
curl -s https://signals.swifttrade.app/health
curl -s https://signals.swifttrade.app/health/supabase-smoke
```

✅ **Check:** Same results as Step 16, over HTTPS.

If this fails: tunnel not routing, backend not listening on 8010, or DNS not propagated (wait a few minutes).

---

## PART F — Web portal (Cloudflare Pages)

### Step 21 — Create Pages project

1. Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**.
2. Select your GitHub repo.
3. **Project name:** e.g. `swifttrade-web`
4. **Production branch:** `main`

### Step 22 — Build settings

| Setting | Value |
|---------|--------|
| **Root directory** | `web` |
| **Build command** | `npm ci && npm run build` |
| **Build output directory** | `.next` (default for Next.js preset) |

If Cloudflare offers a **Next.js** framework preset, use it.

### Step 23 — Environment variables (Pages → Settings → Environment variables)

Add for **Production** (and Preview if you want):

| Variable | Value |
|----------|--------|
| `NEXT_PUBLIC_SUPABASE_URL` | From Step 5 |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | From Step 5 |
| `SUPABASE_SERVICE_ROLE_KEY` | From Step 5 (secret) |
| `STRIPE_SECRET_KEY` | From Step 7 (`sk_test_...` first) |
| `STRIPE_PRICE_ID` | From Step 6 |
| `NEXT_PUBLIC_SITE_URL` | `https://swifttrade.app` |
| `STRIPE_CUSTOMER_PORTAL_RETURN_URL` | `https://swifttrade.app/dashboard` |
| `DESKTOP_SIGNAL_SERVER_URL` | `wss://signals.swifttrade.app/ws/exec` |
| `DESKTOP_APP_VERSION` | `1.0.0` (match your release) |
| `DESKTOP_DOWNLOAD_URL` | Placeholder OK until Step 36 |

Leave `STRIPE_WEBHOOK_SECRET` empty until Step 33.

**Save** all variables.

### Step 24 — First deploy

1. **Save and Deploy** (or push to `main` to trigger build).
2. Wait until build status is **Success**.

✅ **Check:** Pages gives you a `*.pages.dev` URL that loads the site.

> **If the build fails** (common with `output: "standalone"` in `web/next.config.ts`): use **Path F-alt** at the end of this document.

### Step 25 — Custom domain for web

1. Pages project → **Custom domains** → **Set up a custom domain**.
2. Enter: `swifttrade.app` (and optionally `www.swifttrade.app`).
3. Follow DNS instructions (usually automatic on Cloudflare).

✅ **Check:** `https://swifttrade.app` opens the marketing/home page in a browser.

### Step 26 — Supabase redirect (production)

Confirm Step 3 Site URL is `https://swifttrade.app` (not only localhost).

---

## PART G — Stripe webhook (production URL)

### Step 27 — Create webhook endpoint

1. Stripe Dashboard (**Test mode** still ON) → **Developers** → **Webhooks** → **Add endpoint**.
2. **Endpoint URL:** `https://swifttrade.app/api/stripe/webhook`
3. **Select events:**
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
   - `invoice.payment_succeeded`
   - `invoice.paid`
4. **Add endpoint**.

### Step 28 — Add signing secret to Pages

1. Open the new endpoint → reveal **Signing secret** (`whsec_...`).
2. Cloudflare Pages → **Settings** → **Environment variables** → add:
   - `STRIPE_WEBHOOK_SECRET` = `whsec_...`
3. **Redeploy** the Pages project (Deployments → … → **Retry deployment** or push empty commit).

✅ **Check:** Stripe → Webhooks → your endpoint → recent deliveries show **200** after a test checkout (Step 40).

---

## PART H — Desktop app (Windows build + release)

### Step 29 — Build EXE with production WebSocket URL

On your **Windows** dev machine, in repo root:

```powershell
.\desktop\scripts\build-windows.ps1 -DefaultExecutorWsUrl "wss://signals.swifttrade.app/ws/exec"
```

✅ **Check:** File exists: `desktop\dist\SwiftTrade.exe`.

### Step 30 — Create GitHub Release

1. GitHub repo → **Releases** → **Create a new release**.
2. **Tag:** `v1.0.0` (match `DESKTOP_APP_VERSION`).
3. Upload `desktop/dist/SwiftTrade.exe` as release asset.
4. **Publish release**.

### Step 31 — Copy download URL

1. Right-click the release asset **SwiftTrade.exe** → copy link.
2. URL looks like: `https://github.com/USER/REPO/releases/download/v1.0.0/SwiftTrade.exe`

### Step 32 — Update Pages env vars

Set in Cloudflare Pages → Environment variables:

| Variable | Value |
|----------|--------|
| `DESKTOP_DOWNLOAD_URL` | URL from Step 31 |
| `DESKTOP_APP_VERSION` | `1.0.0` |
| `DESKTOP_SIGNAL_SERVER_URL` | `wss://signals.swifttrade.app/ws/exec` |

Redeploy Pages.

✅ **Check:** `https://swifttrade.app/download` shows version and download link works.

---

## PART I — End-to-end verification (do not skip)

### Step 33 — Sign up on production site

1. Open `https://swifttrade.app` → **Sign up** / **Login**.
2. Create account with email/password.

✅ **Check:** You land on dashboard or home while logged in.

### Step 34 — Subscribe (Stripe test card)

1. Dashboard → upgrade / subscribe (your pricing flow).
2. Stripe Checkout → card `4242 4242 4242 4242`, any future expiry, any CVC.
3. Complete payment.

✅ **Check:**

- Stripe webhook delivery **200**.
- Dashboard shows **Pro** / active subscription.
- **License key** visible (UUID format).

### Step 35 — Download and run desktop

1. `https://swifttrade.app/download` → download `SwiftTrade.exe`.
2. Run app → paste **license key** from dashboard.
3. Set WebSocket URL if prompted: should default to `wss://signals.swifttrade.app/ws/exec` (baked in at build).
4. **Paper mode** ON first.
5. Add Trading212 **practice** API keys in settings.
6. Click **Connect**.

✅ **Check:** App shows connected / WS online.

### Step 36 — Test signal (temporary debug)

Production has debug **off** by default. To test once:

1. On server, edit `~/swifttrade/deploy/.env`:

```env
DEBUG_ROUTES_ENABLED=true
DEBUG_API_KEY=your-long-random-secret-here
```

2. Restart:

```bash
cd ~/swifttrade/deploy && docker compose up -d
```

3. From any machine:

```bash
curl -X POST "https://signals.swifttrade.app/debug/broadcast_test_signal" \
  -H "Content-Type: application/json" \
  -H "X-Debug-Key: your-long-random-secret-here" \
  -d "{\"symbol\":\"AAPL\",\"direction\":\"LONG\"}"
```

4. Desktop should show the signal in queue/activity.

5. **Immediately** set back:

```env
DEBUG_ROUTES_ENABLED=false
```

Remove `DEBUG_API_KEY` line. `docker compose up -d` again.

✅ **Check:** Signal appeared; debug is off again.

### Step 37 — Optional: demo live order

1. Confirm-before-trade **ON**.
2. Small size on practice account.
3. Repeat test signal or wait for strategy signal.
4. Confirm order in UI.

✅ **Check:** Order visible in Trading212 practice account.

---

## PART J — Go live (real money) — only after Part I passes

### Step 38 — Stripe live mode

1. Stripe → turn **Test mode OFF** (live).
2. Create **live** product/price OR activate live price → new `STRIPE_PRICE_ID` (`price_...` live).
3. New live **Secret key** `sk_live_...`.
4. New live webhook → `https://swifttrade.app/api/stripe/webhook` → new `whsec_...`.

### Step 39 — Update Cloudflare Pages env

Replace test values with live:

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_ID`

Redeploy.

### Step 40 — Final production checklist

- [ ] `DEBUG_ROUTES_ENABLED=false` on server
- [ ] Supabase Site URL = `https://swifttrade.app`
- [ ] `signals.swifttrade.app/health` OK
- [ ] Friend can: sign up → pay → download → connect in **Paper** without your help
- [ ] Terms / Privacy pages exist or are linked before marketing (recommended)

---

## Path F-alt — Self-host web on home server (if Pages build fails)

### Alt-1 — GitHub secrets for web image (optional)

Add to GitHub Actions secrets (for docker-web workflow):

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_SITE_URL` = `https://swifttrade.app`

Push changes under `web/` to build `veski4a06/swifttrade-web:latest`.

### Alt-2 — Server env file

```bash
cd ~/swifttrade/deploy
cp env.web.example .env.web
nano .env.web   # fill all vars from Step 23 + STRIPE_WEBHOOK_SECRET
```

### Alt-3 — Start web container

```bash
docker compose --profile web up -d
curl -s http://127.0.0.1:3000
```

### Alt-4 — Tunnel route

Zero Trust → add public hostname:

- `swifttrade.app` → `http://localhost:3000`

Skip Cloudflare Pages (Steps 21–25); continue from Step 27 (Stripe webhook) using `https://swifttrade.app`.

---

## Quick reference — all environment variables

### Backend (`~/swifttrade/deploy/.env`)

| Variable | Required | Example |
|----------|----------|---------|
| `SUPABASE_URL` | Yes | `https://xxx.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | `eyJ...` |
| `APP_BASE_URL` | Yes | `https://signals.swifttrade.app` |
| `RUN_DB_MIGRATIONS` | Yes | `false` |
| `DEBUG_ROUTES_ENABLED` | Yes | `false` (prod) |
| `JWT_SECRET` | Yes | long random string |

### Web (Cloudflare Pages or `deploy/.env.web`)

| Variable | Required |
|----------|----------|
| `NEXT_PUBLIC_SUPABASE_URL` | Yes |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes |
| `STRIPE_SECRET_KEY` | Yes |
| `STRIPE_WEBHOOK_SECRET` | Yes (after webhook created) |
| `STRIPE_PRICE_ID` | Yes |
| `NEXT_PUBLIC_SITE_URL` | Yes |
| `DESKTOP_DOWNLOAD_URL` | Yes (after release) |
| `DESKTOP_APP_VERSION` | Yes |
| `DESKTOP_SIGNAL_SERVER_URL` | Yes |

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| WS connect fails / license 4420 | `curl .../health/supabase-smoke` on server; fix Supabase env |
| Webhook 400 | Wrong `STRIPE_WEBHOOK_SECRET`; redeploy web after updating |
| No license after pay | Check Stripe webhook 200; reload dashboard; check Supabase `subscriptions` / `licenses` tables |
| Pages build fails | Use Path F-alt (Docker web) or check build logs for Next.js errors |
| Watchtower not updating | Confirm image tag `latest` on Hub; container name included in Watchtower scope |

---

## Order summary (40 steps)

1–5 Supabase → 6–7 Stripe keys → 9–11 Docker CI → 12–17 Server backend → 18–20 Tunnel API → 21–26 Pages web → 27–28 Stripe webhook → 29–32 EXE release → 33–37 E2E test → 38–40 Go live
