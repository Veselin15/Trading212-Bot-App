# MVP checklist

One paying user path: **sign up → pay → license → download → connect → signal → paper/demo trade**.

---

## Phase 1 — Local E2E (do this first)

### Supabase

- [ ] Project created; migrations applied (`supabase/migrations/` in order)
- [ ] Auth email provider on; redirect URLs include `http://localhost:3000/auth/callback`
- [ ] `web/.env.local`: `NEXT_PUBLIC_SUPABASE_*`, `SUPABASE_SERVICE_ROLE_KEY`
- [ ] `backend/.env`: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`

### Stripe (test mode)

- [ ] Recurring price → `STRIPE_PRICE_ID`
- [ ] `web/.env.local`: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`
- [ ] Webhook via `docker compose --profile stripe up stripe-cli` or `npm run stripe:listen`
- [ ] Events listed in `web/ENV.md`

### Run stack

```powershell
# Terminal 1
.\dev.ps1

# Terminal 2
cd web; npm run dev
```

- [ ] Dashboard: sign up → subscribe (card `4242…`) → copy license key
- [ ] Desktop: license optional in **Paper**; WS `ws://127.0.0.1:8011/ws/exec` (dev.ps1 port)
- [ ] Test signal:

```powershell
Invoke-RestMethod -Method POST -Uri "http://127.0.0.1:8011/debug/broadcast_test_signal" `
  -ContentType "application/json" `
  -Body '{"symbol":"AAPL","direction":"LONG"}'
```

(Enable debug locally: `DEBUG_ROUTES_ENABLED=true` in `backend/.env` if routes return 404.)

- [ ] Signal appears in desktop queue / activity
- [ ] Optional: T212 **practice** keys, switch to Live + confirm-before-trade, repeat test signal

**Exit:** subscribe → license → WS online → test signal → optional demo order.

---

## Phase 2 — Production (`swifttrade.app`)

### Infra

- [ ] GitHub secrets: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`
- [ ] Push `main` → backend image on Docker Hub
- [ ] Server: `deploy/.env` from `deploy/env.backend.example`
- [ ] `docker compose -f deploy/docker-compose.yml up -d`
- [ ] Tunnel: `signals.swifttrade.app` → `localhost:8010`
- [ ] `curl https://signals.swifttrade.app/health/supabase-smoke` shows non-zero url/key lengths

### Web

- [ ] Cloudflare Pages **or** `docker compose --profile web` + tunnel to `:3000`
- [ ] Production env from `deploy/env.web.example` / `web/ENV.md`
- [ ] Stripe live/test webhook → `https://swifttrade.app/api/stripe/webhook`
- [ ] Supabase Site URL + redirect = `https://swifttrade.app`

### Desktop release

```powershell
.\desktop\scripts\build-windows.ps1 -DefaultExecutorWsUrl "wss://signals.swifttrade.app/ws/exec"
```

- [ ] Upload EXE; set `DESKTOP_DOWNLOAD_URL`, `DESKTOP_APP_VERSION`, `DESKTOP_SIGNAL_SERVER_URL`

### Lockdown

- [ ] `DEBUG_ROUTES_ENABLED=false` on public backend
- [ ] Friend test: sign up → pay → download → paper connect → no manual help

**Exit:** stranger completes flow without your machine.

---

## Phase 3 — Post-MVP (defer)

- [ ] Marketing copy: WS path vs Supabase Realtime (`signals` table unused)
- [ ] Break-even polling on desktop
- [ ] Portal signal history
- [ ] CI for desktop EXE
- [ ] Terms / Privacy pages before broad marketing

---

## Env quick reference

| Var | Where |
|-----|--------|
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | `backend/.env`, web server |
| `NEXT_PUBLIC_SUPABASE_*` | web (build-time for Pages) |
| `STRIPE_*` | web only |
| `DESKTOP_*` | web display / download |
| `RUN_DB_MIGRATIONS=false` | production backend |
| `DEBUG_ROUTES_ENABLED` | backend; `false` in prod |
