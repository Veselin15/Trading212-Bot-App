-- Trading212 Bot App (Supabase)
-- Init schema for subscriptions gating + realtime signals.

-- Extensions commonly available on Supabase.
create extension if not exists "pgcrypto";

-- 1) Subscriptions: updated by Stripe webhook (service role).
create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,

  stripe_customer_id text unique,
  stripe_subscription_id text unique,

  status text not null default 'inactive',
  current_period_end timestamptz,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists subscriptions_user_id_idx on public.subscriptions (user_id);
create index if not exists subscriptions_status_idx on public.subscriptions (status);

-- Keep updated_at current.
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists subscriptions_set_updated_at on public.subscriptions;
create trigger subscriptions_set_updated_at
before update on public.subscriptions
for each row execute function public.set_updated_at();

-- Helper: define "active" subscription as status=active and not past period end (if present).
create or replace function public.has_active_subscription(p_user_id uuid)
returns boolean
language sql
stable
as $$
  select exists (
    select 1
    from public.subscriptions s
    where s.user_id = p_user_id
      and s.status = 'active'
      and (s.current_period_end is null or s.current_period_end > now())
  );
$$;

alter table public.subscriptions enable row level security;

-- Users can read their own subscription row.
drop policy if exists subscriptions_select_own on public.subscriptions;
create policy subscriptions_select_own
on public.subscriptions
for select
to authenticated
using (user_id = auth.uid());

-- No client-side writes. (Service role bypasses RLS.)
drop policy if exists subscriptions_no_insert on public.subscriptions;
create policy subscriptions_no_insert
on public.subscriptions
for insert
to authenticated
with check (false);

drop policy if exists subscriptions_no_update on public.subscriptions;
create policy subscriptions_no_update
on public.subscriptions
for update
to authenticated
using (false)
with check (false);

drop policy if exists subscriptions_no_delete on public.subscriptions;
create policy subscriptions_no_delete
on public.subscriptions
for delete
to authenticated
using (false);

-- 2) Signals: inserted only by the Python Brain worker (service role).
create table if not exists public.signals (
  id uuid primary key default gen_random_uuid(),
  trade_id text not null unique,
  ticker text not null,
  action text not null check (action in ('BUY', 'SELL')),
  sl_pct numeric,
  tp_pct numeric,
  created_at timestamptz not null default now()
);

create index if not exists signals_created_at_idx on public.signals (created_at desc);

alter table public.signals enable row level security;

-- Only subscribed users can read signals.
drop policy if exists signals_select_active_subscriber on public.signals;
create policy signals_select_active_subscriber
on public.signals
for select
to authenticated
using (public.has_active_subscription(auth.uid()));

-- Disallow all client-side writes.
drop policy if exists signals_no_insert on public.signals;
create policy signals_no_insert
on public.signals
for insert
to authenticated
with check (false);

drop policy if exists signals_no_update on public.signals;
create policy signals_no_update
on public.signals
for update
to authenticated
using (false)
with check (false);

drop policy if exists signals_no_delete on public.signals;
create policy signals_no_delete
on public.signals
for delete
to authenticated
using (false);

