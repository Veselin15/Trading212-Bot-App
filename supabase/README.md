# Supabase

This folder keeps **repeatable** schema changes for your Supabase project.

## Apply migrations

- Create a Supabase project.
- Run the SQL in [`supabase/migrations/`](migrations/) in order (oldest → newest) using the Supabase SQL Editor or the Supabase CLI.

## Tables

- `public.subscriptions`: Stripe-driven subscription state per user.
- `public.signals`: Insert-only stream of trading signals (readable only by active subscribers via RLS).

