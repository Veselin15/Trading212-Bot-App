## Project structure goals

This project is split by runtime boundary so each piece can evolve independently.

### Boundaries

- **Web (`web/`)**: UI + route handlers (Stripe, license regeneration). Reads/writes Supabase.
- **Backend (`backend/`)**: WebSocket gateway + strategy runner. Validates licenses against Supabase; **guest paper mode** accepts connections without a license when `mode: paper`.
- **Desktop (`desktop/`)**: End-user **`SwiftTrade.exe`** (PyInstaller, no console). Dev source runs via `pyw` / `launch-dev.ps1`.
- **Supabase (`supabase/`)**: Source of truth for subscriptions, signals, and licenses.
- **Server-App (`Server-App/t212_miner_bot/`)**: Strategy logic consumed by the backend runner (not a separate deployable in MVP).

### Dev ports

| Context | Backend port | Desktop default WS |
|---------|--------------|-------------------|
| `dev.ps1` / `stop.ps1` | 8011 | `ws://127.0.0.1:8011/ws/exec` |
| Docker / release EXE | 8010 | `ws://127.0.0.1:8010/ws/exec` (or production URL via build) |

### Conventions

- Keep “integration glue” in one place (e.g. `backend/app/integrations/*`) so API routes stay small.
- Keep UI primitives in `web/src/components/ui/*`.
- Prefer shared business types in `shared/` (payload shapes, enums) once both backend and desktop need them.

