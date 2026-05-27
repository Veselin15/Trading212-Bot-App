# Supabase

The **web portal** uses your hosted Supabase project for accounts, billing state, and license keys. The local **Docker Postgres** (`docker-compose.yml`) is only for the Python trading backend — not for login or subscriptions.

## Where data is stored

| Data | Location |
|------|----------|
| User accounts (email, password, OAuth) | Supabase **`auth.users`** (managed Auth API) |
| Subscription status, Stripe IDs | Supabase **`public.subscriptions`** |
| Desktop license keys | Supabase **`public.licenses`** |
| Trading signals (Pro feed) | Supabase **`public.signals`** |
| Bot positions / strategy state | Local **Postgres** via `docker compose` (backend only) |

There is no separate `profiles` table: the account **is** the row in `auth.users`. The dashboard shows `user.email` from that record.

## Apply migrations (required once per project)

1. Open [Supabase Dashboard](https://supabase.com/dashboard) → your project → **SQL Editor**.
2. Run each file in [`supabase/migrations/`](migrations/) **in order** (oldest date first):
   - `20260428_000001_init_subscriptions_signals.sql`
   - `20260428_000002_init_licenses.sql`
   - `20260428_000003_add_license_enforcement_fields.sql`

If tables are missing, the dashboard shows a setup warning.

## Auth settings (recommended for local dev)

In **Authentication → Providers → Email**:

- For fastest local testing, you can disable **Confirm email** so sign-up logs in immediately.
- If confirmation is enabled, users must click the link in email before signing in (the portal shows instructions after sign-up).

Add **Site URL** / redirect URLs under **Authentication → URL configuration**:

- Site URL: `http://localhost:3000` (or your production domain)
- Redirect URLs: `http://localhost:3000/auth/callback`

## Stripe + Supabase flow

1. User signs up / signs in → session cookie (Supabase Auth).
2. **Upgrade to Pro** → Stripe Checkout; a `subscriptions` row links `user_id` ↔ `stripe_customer_id`.
3. Stripe webhook (or dashboard refresh) sets `status`, `current_period_end`, and creates a `licenses` row.
4. Desktop app uses the license key; backend validates against Supabase.

See `web/ENV.md` for Stripe webhook setup.
