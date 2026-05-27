## SwiftTrade (Trading212 Bot App)

Web portal, FastAPI backend, and Windows desktop executor for Trading212.

**MVP tiers**


| Tier | License | Trading |
|------|---------|---------|
| **Paper / Free** | Optional — leave license blank | Practice (demo) account only |
| **Pro** | Required UUID from dashboard | Live account + full features |

### Project layout

| Path | Role |
|------|------|
| `web/` | Next.js portal — Supabase Auth, Stripe, license keys, download page |
| `backend/` | FastAPI — WebSocket gateway, license validation, strategy signal broadcaster |
| `desktop/` | PySide6 executor — encrypted T212 keys, WS client, order placement |
| `supabase/` | Migrations for subscriptions, signals, licenses |
| `Server-App/` | Strategy source (`t212_miner_bot`) imported by the backend runner |
| `shared/` | Shared types (grows over time) |
| `scripts/` | Dev helpers (e.g. Stripe webhook forwarding) |

### Prerequisites

- **Python 3.12+** (desktop needs PySide6; use `py -3.12` on Windows if `python` is older)
- **Node.js 20+** for the web app
- **Docker Desktop** for local Postgres (used by `dev.ps1`)
- Copy env files: `backend/.env.example` → `backend/.env`, see `web/ENV.md`

### Quick start (Windows)

```powershell
# 1. Install dependencies (once)
pip install -r backend/requirements.txt
pip install -r desktop/requirements.txt
cd web; npm install; cd ..

# 2. Backend + desktop (Postgres via Docker)
.\dev.ps1

# 3. Web (separate terminal)
cd web
npm run dev
```

**Ports**

- Local dev (`dev.ps1`): backend **8011** — `http://127.0.0.1:8011`, WS `ws://127.0.0.1:8011/ws/exec`
- Docker / release EXE: **8010** (see `docker-compose.yml`, `build-windows.ps1`)

**End users** download and double-click **`SwiftTrade.exe`** from the web portal — a normal Windows GUI app with no console or `.bat` file.

Build the EXE (once per release):

```powershell
.\desktop\scripts\build-windows.ps1 -DefaultExecutorWsUrl "wss://your-api.example.com/ws/exec"
```

Output: `desktop/dist/SwiftTrade.exe` — ship this file to customers.

**Developers** run the GUI from source without a console via `.\dev.ps1` or `.\desktop\scripts\launch-dev.ps1` (uses `pyw` / `pythonw`).

**Stop dev processes:** `.\stop.ps1`

### Paper mode (no license)

1. Start backend (`dev.ps1` or uvicorn on port 8011).
2. Open desktop → leave license key empty → connect.
3. Use a Trading212 **practice** API key in settings.
4. Toggle **Paper** mode in the app.

Pro users: copy license key from the web dashboard after subscribing.

### Environment

- Web: `web/ENV.md`
- Backend: `backend/.env.example` (Supabase service role for license validation)

### MVP checklist (before launch)

See **[docs/MVP_CHECKLIST.md](docs/MVP_CHECKLIST.md)** (local E2E + production) and **[docs/DEPLOY.md](docs/DEPLOY.md)** (Docker Hub, home server, Cloudflare Tunnel, `swifttrade.app`).

See `docs/PROJECT_STRUCTURE.md` for architecture notes.
