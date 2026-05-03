# Web portal environment variables

## Required (Supabase)

- `NEXT_PUBLIC_SUPABASE_URL` 
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

## Required (Stripe)

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_ID` (the recurring subscription price id)

## Required (Supabase service role, server-only)

- `SUPABASE_SERVICE_ROLE_KEY` 

## Optional

- `NEXT_PUBLIC_SITE_URL` (default `http://localhost:3000`)
- `STRIPE_CUSTOMER_PORTAL_RETURN_URL` (default `${NEXT_PUBLIC_SITE_URL}/dashboard`)
- `DESKTOP_DOWNLOAD_URL` (link to installer, e.g. GitHub Releases asset URL)
- `DESKTOP_APP_VERSION` (display-only version string shown on /download, e.g. `1.0.0`)
- `DESKTOP_CHANGELOG_URL` (optional link to release notes)
- `DESKTOP_SIGNAL_SERVER_URL` (display-only — the wss:// address baked into the EXE, shown on /download so users know which server their app connects to)

