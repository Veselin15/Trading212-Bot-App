-- Trading212 Bot App (Supabase)
-- 14-day trial + tier model.
--
-- Effective tier is computed at read time from (trial_ends_at, active subscription):
--   active Stripe subscription            -> PRO
--   else trial_ends_at still in the future -> TRIAL
--   else                                   -> EXPIRED
--
-- `profiles.subscription_tier` is a denormalized hint kept in sync by the Stripe
-- webhook (PRO on active, EXPIRED on terminal). Trial *expiry* is time-based, so
-- access checks below always recompute it rather than trusting the column.

create extension if not exists "pgcrypto";

-- 1) Profiles: one row per auth user, created on signup with a 14-day trial.
create table if not exists public.profiles (
  user_id uuid primary key references auth.users (id) on delete cascade,

  subscription_tier text not null default 'TRIAL'
    check (subscription_tier in ('TRIAL', 'PRO', 'EXPIRED')),
  trial_ends_at timestamptz,

  -- Email-drip scaffold (Phase 5). Wired later; tracked here so sends are idempotent.
  welcome_email_sent_at timestamptz,
  day7_email_sent_at timestamptz,
  day13_email_sent_at timestamptz,
  expired_email_sent_at timestamptz,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- set_updated_at() is defined in 20260428_000001_init_subscriptions_signals.sql.
drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at
before update on public.profiles
for each row execute function public.set_updated_at();

-- 2) Auto-create a trial profile when a new auth user signs up.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (user_id, subscription_tier, trial_ends_at)
  values (new.id, 'TRIAL', now() + interval '14 days')
  on conflict (user_id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();

-- 3) Backfill profiles for users created before this migration.
insert into public.profiles (user_id, subscription_tier, trial_ends_at)
select u.id, 'TRIAL', now() + interval '14 days'
from auth.users u
left join public.profiles p on p.user_id = u.id
where p.user_id is null;

-- Existing paying users should not be dropped into a trial.
update public.profiles p
set subscription_tier = 'PRO', trial_ends_at = null
where public.has_active_subscription(p.user_id)
  and p.subscription_tier <> 'PRO';

-- 4) Access helpers.

-- Signal feed access: active subscriber OR inside an unexpired trial.
create or replace function public.has_signal_access(p_user_id uuid)
returns boolean
language sql
stable
as $$
  select
    public.has_active_subscription(p_user_id)
    or exists (
      select 1
      from public.profiles pr
      where pr.user_id = p_user_id
        and pr.trial_ends_at is not null
        and pr.trial_ends_at > now()
    );
$$;

-- Effective tier as seen by enforcement (backend mirrors this in Python).
create or replace function public.effective_tier(p_user_id uuid)
returns text
language sql
stable
as $$
  select case
    when public.has_active_subscription(p_user_id) then 'PRO'
    when exists (
      select 1 from public.profiles pr
      where pr.user_id = p_user_id
        and pr.trial_ends_at is not null
        and pr.trial_ends_at > now()
    ) then 'TRIAL'
    else 'EXPIRED'
  end;
$$;

-- 5) RLS on profiles: users read their own; no client writes (service role bypasses).
alter table public.profiles enable row level security;

drop policy if exists profiles_select_own on public.profiles;
create policy profiles_select_own
on public.profiles
for select
to authenticated
using (user_id = auth.uid());

drop policy if exists profiles_no_insert on public.profiles;
create policy profiles_no_insert
on public.profiles
for insert
to authenticated
with check (false);

drop policy if exists profiles_no_update on public.profiles;
create policy profiles_no_update
on public.profiles
for update
to authenticated
using (false)
with check (false);

drop policy if exists profiles_no_delete on public.profiles;
create policy profiles_no_delete
on public.profiles
for delete
to authenticated
using (false);

-- 6) Re-point the signals read policy from "active subscriber" to "trial OR active".
--    Trial users must be able to paper-trade the algorithm's signals.
drop policy if exists signals_select_active_subscriber on public.signals;
drop policy if exists signals_select_trial_or_subscriber on public.signals;
create policy signals_select_trial_or_subscriber
on public.signals
for select
to authenticated
using (public.has_signal_access(auth.uid()));
