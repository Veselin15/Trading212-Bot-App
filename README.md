## Trading212 Bot App

This repo contains a **web portal**, a **FastAPI backend**, and a **Windows desktop executor**.

### Project layout

- `web/`: Next.js portal (Supabase Auth + Stripe, license key UI)
- `backend/`: FastAPI backend (WebSocket executor gateway, strategy runner)
- `desktop/`: PySide6 desktop executor (encrypted keys + WS client)
- `supabase/`: Supabase migrations + notes (subscriptions/signals/licenses)
- `Server-App/`: legacy bot code (kept for strategy/execution experiments)
- `shared/`: shared types/utilities (grows over time)

### Local development (Windows)

- **All-in-one**: run `dev.ps1` (starts Postgres via Docker + backend + desktop; web is separate)
- **Web**:
  - `cd web`
  - `npm install`
  - `npm run dev`
- **Backend**:
  - create `backend/.env` based on `backend/.env.example`
  - `pip install -r backend/requirements.txt`
  - `PYTHONPATH=backend uvicorn app.main:app --reload --port 8000`
- **Desktop**:
  - `pip install -r desktop/requirements.txt`
  - `python -m desktop.app.main`

### Environment variables

- Web: see `web/ENV.md`
- Backend: see `backend/.env.example` (includes Supabase service role for license validation)

