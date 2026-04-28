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
- `STRIPE_CUSTOMER_PORTAL_RETURN_URL` (default `${NEXT_PUBLIC_SITE_URL}/account`)
- `DESKTOP_DOWNLOAD_URL` (link to installer, e.g. GitHub Releases asset)
- `DESKTOP_APP_VERSION` (display-only)
- `DESKTOP_CHANGELOG_URL` (optional link to release notes)

