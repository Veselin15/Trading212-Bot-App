---
name: Trading212 licensing+ws+desktop
overview: "Implement a Python-first architecture: FastAPI backend with Postgres + Stripe webhooks for licensing, a WebSocket connection pool enforcing one-license-per-IP, and a PySide6 desktop executor with encrypted local Trading212 credentials, auto-reconnect, and resilient Trading212 API calls."
todos:
  - id: design-db-schema
    content: Define Postgres schema for users/licenses + migrations tooling.
    status: in_progress
  - id: stripe-webhooks
    content: Implement Stripe webhook endpoint to activate/suspend licenses.
    status: pending
  - id: ws-connection-pool
    content: Implement WS handshake, IP lock, heartbeat ping/pong, and connection registry.
    status: pending
  - id: signal-pipeline
    content: Refactor strategy to emit normalized signals and broadcast to WS clients.
    status: pending
  - id: desktop-app
    content: Create PySide6 desktop app with encrypted local Trading212 key storage, auto-reconnect, and execution module with backoff + position polling.
    status: pending
isProject: false
---

# Trading212 Bot Platform Build Plan

## Scope (what we will build first)
- **Component 2 (Server/Core Engine)**: FastAPI backend providing Stripe webhook handling, licensing DB, and a WebSocket manager that broadcasts strategy signals to connected desktop executors.
- **Component 3 (Desktop Executor)**: PySide6 desktop app that stores Trading212 credentials encrypted locally, maintains a resilient WS connection, executes Trading212 API calls with exponential backoff, and manages positions locally.
- **Component 1 (Web Platform)**: Minimal user portal endpoints for license view/regenerate + download link. Full storefront UI can come later; we’ll build the backend primitives now.

## Repo reality check (what exists today)
- Your current workspace contains only a Python bot under `[Server-App/t212_miner_bot/](Server-App/t212_miner_bot/)` (asyncio + `aiohttp`) and no Stripe/Postgres/WebSocket/desktop yet.
- We will **not** mix in `[Projects/AI-Interview-Assistant/](../AI-Interview-Assistant/)` (separate product). We’ll keep this project self-contained.

## Target architecture (end-to-end)

```mermaid
flowchart LR
  stripe[Stripe] -->|invoice.payment_succeeded
  invoice.payment_failed| api[FastAPI_Backend]
  portalUser[Portal_User] -->|login_dashboard| api
  api --> db[(Postgres)]

  strategy[Strategy_Module] -->|broadcast_signal(signal_json)| api
  api -->|WS_broadcast| desktop[PySide6_Desktop_App]
  desktop -->|Trading212_REST| t212[Trading212_API]

  api -->|download_link_latest| desktop
```

## Data model (Postgres)
We’ll implement the two core tables you specified plus a couple pragmatic fields to support Stripe and key rotation.

- **`users`**
  - `id` (uuid pk)
  - `email` (unique)
  - `password_hash`
  - `stripe_customer_id` (unique nullable)
  - `created_at`

- **`licenses`**
  - `id` (uuid pk)
  - `license_key` (uuid unique, the key the desktop uses)
  - `user_id` (fk)
  - `status` (enum: `active`, `suspended`, `expired`)
  - `expires_at` (timestamp with tz)
  - `last_ip_address` (inet nullable)
  - `last_seen_at` (timestamp with tz nullable)
  - `revoked_at` (timestamp with tz nullable)
  - `created_at`

Notes:
- We’ll make **license regeneration** create a *new* license key (or rotate within same row) and immediately invalidate old connections.
- `last_ip_address` is used for **one-license-per-IP** enforcement; we can later evolve to machine-bound fingerprints.

## Stripe webhook logic
Implement a webhook endpoint that:
- Verifies signatures (Stripe signing secret).
- On `invoice.payment_succeeded`:
  - Find user by `stripe_customer_id`.
  - Create or extend license: set `status=active`, bump `expires_at` (e.g., add 30 days or read period end from Stripe).
- On `invoice.payment_failed` (and optionally `customer.subscription.deleted`):
  - Set license `status=suspended` (or `expired` if past grace window), and prevent WS connections.

## WebSocket protocol (server ↔ desktop)
We’ll use simple JSON messages with explicit types.

- **Client → Server**
  - `{"type":"HELLO","license_key":"..."}`
  - `{"type":"PONG"}`
  - Optional acknowledgements: `{"type":"ACK","signal_id":"..."}`

- **Server → Client**
  - `{"type":"PING"}` every 30s
  - Signal broadcast:

```json
{"type":"SIGNAL","payload":{"id":"unique_trade_id","type":"ENTRY","direction":"LONG","symbol":"AAPL","risk_params":{"stop_loss_pct":2.0,"take_profit_pct":6.0}}}
```

## Connection pool + anti-cheat
Server maintains an in-memory registry keyed by `license_id`:
- On connect: validate license (active, not expired) and record remote IP.
- **IP lock**:
  - If license already connected from a different IP, reject the new connection.
  - If same IP reconnects, replace old connection cleanly.
- Heartbeat:
  - Server sends `PING` every 30 seconds.
  - If `PONG` not received within a deadline (e.g., 10 seconds), mark offline and remove from pool.

## Strategy abstraction (signal pipeline)
We’ll refactor the current bot so it no longer “executes” trades directly in the server process.
- Keep your existing signal generation logic under `[Server-App/t212_miner_bot/](Server-App/t212_miner_bot/)`.
- Introduce a new strategy entrypoint (e.g. `strategy/strategy.py`) that produces normalized signals and calls `broadcast_signal(payload)`.
- Initially, we can implement `broadcast_signal` as a local function inside the backend process; later we can split strategy into a separate worker if needed.

## Desktop app (PySide6) responsibilities
- **Minimal UI**: traffic-light connection status + license key field + Trading212 key field.
- **Local encryption**:
  - Use `cryptography` (Fernet) to encrypt Trading212 credentials.
  - Derive the encryption key from a machine-specific secret (Windows: `MachineGuid` from registry + DPAPI or a KDF). Practical default:
    - Use Windows DPAPI via `win32crypt` if acceptable, else use a KDF (PBKDF2) with `MachineGuid` as part of the salt.
- **Auto-reconnect**:
  - Infinite reconnect loop; if WS drops, set status to Connecting and retry every 5 seconds.
- **Execution module**:
  - Implement Trading212 REST calls with robust retries.
  - On HTTP 429, do exponential backoff (1s, 2s, 4s… capped).
- **Local position management**:
  - Background poll every 10–15 seconds.
  - When break-even threshold hit (e.g. +1.5%), submit stop-loss move.

## Project structure (new)
Create clear boundaries so it scales:
- `[backend/](backend/)` FastAPI app (Stripe + licensing + WS)
- `[desktop/](desktop/)` PySide6 app
- `[shared/](shared/)` shared types (signal schema, enums) to keep payload stable
- Keep existing bot code under `[Server-App/t212_miner_bot/](Server-App/t212_miner_bot/)` but refactor it into “strategy only” usage.

## Milestones (reviewable increments)
1. **DB + migrations**: Postgres schema + migrations + minimal CRUD for users/licenses.
2. **Stripe webhooks**: verify signatures; update licenses on Stripe events.
3. **WebSocket manager**: handshake + IP lock + ping/pong + connection registry.
4. **Signal broadcast API**: internal `broadcast_signal()` + test broadcast to connected clients.
5. **Desktop skeleton**: UI + encrypted credential storage + WS connect/reconnect + ping/pong.
6. **Desktop execution**: Trading212 client + backoff + position polling + break-even stop logic.
7. **User portal endpoints**: license view/regenerate; download-link endpoint.

## Operational basics (so it runs reliably)
- Environment variables:
  - Backend: `DATABASE_URL`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `APP_BASE_URL`
  - Desktop: license key + encrypted Trading212 creds stored locally
- Local dev: Dockerized Postgres + backend run command + desktop run command.

## What I need next (after you accept the plan)
- Stripe setup details (products/prices and whether you use subscriptions). If unknown, we’ll implement using invoice events + customer id mapping and adjust once Stripe product model is finalized.
