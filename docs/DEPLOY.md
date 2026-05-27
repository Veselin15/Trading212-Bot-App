# SwiftTrade deployment (MVP)

**Strict linear guide:** [DEPLOY_STEP_BY_STEP.md](./DEPLOY_STEP_BY_STEP.md) (follow every step in order).

Target domain: **swifttrade.app** (Cloudflare).

Recommended split (fits a low-CPU home server):

| Service | Where | Public URL |
|---------|--------|------------|
| **Web portal** | Cloudflare Pages (build on push) | `https://swifttrade.app` |
| **Signal backend** | Docker on home server + Cloudflare Tunnel | `https://signals.swifttrade.app` |
| **Desktop** | GitHub Releases (built on your PC) | Download link in portal |

Stripe webhooks hit the **web** app only: `https://swifttrade.app/api/stripe/webhook`.

---

## 1. Supabase (once)

1. Create a project at [supabase.com](https://supabase.com).
2. SQL Editor → run migrations in order from `supabase/migrations/`.
3. **Authentication → URL configuration**
   - Site URL: `https://swifttrade.app`
   - Redirect URLs: `https://swifttrade.app/auth/callback`
4. Copy **Project URL**, **anon key**, **service role key** for web + backend env.

---

## 2. Stripe (test first, then live)

1. Create a recurring **Price** → `STRIPE_PRICE_ID`.
2. Webhook endpoint: `https://swifttrade.app/api/stripe/webhook`
3. Events: `checkout.session.completed`, `customer.subscription.*`, `invoice.payment_failed`, `invoice.payment_succeeded`, `invoice.paid`
4. Signing secret → `STRIPE_WEBHOOK_SECRET` on the web host.

---

## 3. GitHub Actions → Docker Hub

Add repository secrets:

| Secret | Purpose |
|--------|---------|
| `DOCKERHUB_USERNAME` | e.g. `veski4a06` |
| `DOCKERHUB_TOKEN` | Docker Hub access token |
| `NEXT_PUBLIC_SUPABASE_URL` | Baked into web image (optional if using Pages) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Same |
| `NEXT_PUBLIC_SITE_URL` | `https://swifttrade.app` |

Workflows:

- `.github/workflows/docker-backend.yml` → `veski4a06/swifttrade-backend:latest`
- `.github/workflows/docker-web.yml` → `veski4a06/swifttrade-web:latest` (only if self-hosting web)

Push to `main` to build. **Watchtower** on the server pulls new tags every ~5 minutes.

---

## 4. Home server — signal backend

On the Ubuntu server (SSH):

```bash
mkdir -p ~/swifttrade && cd ~/swifttrade
# Copy deploy/docker-compose.yml and create .env from deploy/env.backend.example
nano .env   # SUPABASE_*, APP_BASE_URL, RUN_DB_MIGRATIONS=false, DEBUG_ROUTES_ENABLED=false
docker compose pull
docker compose up -d
curl -s http://127.0.0.1:8010/health
curl -s http://127.0.0.1:8010/health/supabase-smoke
```

`deploy/docker-compose.yml` expects `deploy/.env` beside it. Set:

- `RUN_DB_MIGRATIONS=false` (Supabase is licensing source of truth)
- `DEBUG_ROUTES_ENABLED=false` on the public internet

Persisted bot state: Docker volume `swifttrade_bot_state`.

---

## 5. Cloudflare Tunnel routes

In **Zero Trust → Networks → Tunnels** (your existing `cloudflared`):

| Public hostname | Service |
|-----------------|---------|
| `signals.swifttrade.app` | `http://localhost:8010` |
| `swifttrade.app` | Pages **or** `http://localhost:3000` if using `--profile web` |

WebSocket: Cloudflare proxies `wss://signals.swifttrade.app/ws/exec` to the backend automatically when HTTP is configured to port 8010.

Smoke test from any machine:

```bash
curl -s https://signals.swifttrade.app/health
curl -s https://signals.swifttrade.app/health/supabase-smoke
```

---

## 6. Web portal

### Option A — Cloudflare Pages (recommended)

1. Pages → Create project → connect this GitHub repo.
2. Root directory: `web`
3. Build: `npm ci && npm run build`
4. Output: Next.js default (or `.next` if using adapter; for stock Next 16 on Pages, use **Next.js preset** if offered).
5. Environment variables: all keys from `web/ENV.md` and `deploy/env.web.example`.
6. Custom domain: `swifttrade.app`.

### Option B — Docker on the server

```bash
cd ~/swifttrade
cp deploy/env.web.example .env.web
# fill secrets
docker compose --profile web up -d
```

Tunnel: `swifttrade.app` → `http://localhost:3000`.

---

## 7. Desktop EXE

On your Windows dev machine:

```powershell
.\desktop\scripts\build-windows.ps1 -DefaultExecutorWsUrl "wss://signals.swifttrade.app/ws/exec"
```

Upload `desktop/dist/SwiftTrade.exe` to GitHub Releases, then set on the web host:

- `DESKTOP_DOWNLOAD_URL`
- `DESKTOP_APP_VERSION`
- `DESKTOP_SIGNAL_SERVER_URL=wss://signals.swifttrade.app/ws/exec`

---

## 8. Debug / test signals (production)

With `DEBUG_ROUTES_ENABLED=false`, `/debug/*` is not mounted.

For a controlled test after deploy:

1. Temporarily set `DEBUG_ROUTES_ENABLED=true` and `DEBUG_API_KEY=<long-random>` in `deploy/.env`.
2. Restart backend; call:

```bash
curl -X POST "https://signals.swifttrade.app/debug/broadcast_test_signal" \
  -H "Content-Type: application/json" \
  -H "X-Debug-Key: YOUR_KEY" \
  -d '{"symbol":"AAPL","direction":"LONG"}'
```

3. Turn debug off again.

---

## 9. Watchtower

Ensure the backend container is labeled or included in Watchtower’s scope, e.g.:

```yaml
# in your global watchtower compose (example)
command: --interval 300 --cleanup
```

Only images you pull via `deploy/docker-compose.yml` will auto-update.

---

## Local MVP (before public DNS)

See [MVP_CHECKLIST.md](./MVP_CHECKLIST.md) — Phase 1 with `dev.ps1`, Stripe test mode, and `POST /debug/broadcast_test_signal` on localhost.
