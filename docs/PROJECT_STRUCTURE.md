## Project structure goals

This project is split by runtime boundary so each piece can evolve independently.

### Boundaries

- **Web (`web/`)**: UI + route handlers (Stripe, license regeneration). Reads/writes Supabase.
- **Backend (`backend/`)**: WebSocket gateway + strategy runner. Validates `license_key` against Supabase and enforces IP lock.
- **Desktop (`desktop/`)**: end-user executor. Stores Trading212 keys encrypted locally and connects to backend WS using `license_key`.
- **Supabase (`supabase/`)**: source-of-truth for subscriptions/signals/licenses used by web + backend.

### Conventions

- Keep “integration glue” in one place (e.g. `backend/app/integrations/*`) so API routes stay small.
- Keep UI primitives in `web/src/components/ui/*`.
- Prefer shared business types in `shared/` (payload shapes, enums) once both backend and desktop need them.

