-- Trading212 Bot App (Supabase)
-- Two paid tiers: STARTER (core signals, live, capped positions) and PRO (full
-- signal feed, live, higher position cap). TRIAL stays paper-only; EXPIRED locks out.
--
-- Effective tier (read-time):
--   active subscription, plan='pro'      -> PRO
--   active subscription, plan='starter'  -> STARTER
--   active subscription, plan is null    -> PRO   (legacy single-price installs)
--   else trial_ends_at in the future     -> TRIAL
--   else                                 -> EXPIRED
--
-- The price-id -> plan mapping lives in the web layer (env: STRIPE_PRICE_ID_STARTER /
-- STRIPE_PRICE_ID_PRO). The webhook denormalizes the resolved plan into
-- `subscriptions.plan`, so SQL / backend / web all read one column.

-- 1) Which paid plan an active subscription is on.
alter table public.subscriptions
  add column if not exists plan text
    check (plan is null or plan in ('starter', 'pro'));

-- 2) Allow STARTER as a denormalized profile tier hint.
alter table public.profiles
  drop constraint if exists profiles_subscription_tier_check;
alter table public.profiles
  add constraint profiles_subscription_tier_check
    check (subscription_tier in ('TRIAL', 'STARTER', 'PRO', 'EXPIRED'));

-- 3) Effective tier now distinguishes STARTER vs PRO by the active subscription's plan.
create or replace function public.effective_tier(p_user_id uuid)
returns text
language sql
stable
as $$
  with active_sub as (
    select s.plan
    from public.subscriptions s
    where s.user_id = p_user_id
      and s.status = 'active'
      and (s.current_period_end is null or s.current_period_end > now())
    order by s.created_at desc
    limit 1
  )
  select case
    when exists (select 1 from active_sub) then
      case
        when (select plan from active_sub) = 'starter' then 'STARTER'
        else 'PRO'
      end
    when exists (
      select 1 from public.profiles pr
      where pr.user_id = p_user_id
        and pr.trial_ends_at is not null
        and pr.trial_ends_at > now()
    ) then 'TRIAL'
    else 'EXPIRED'
  end;
$$;

-- has_signal_access() (trial OR active subscriber) is unchanged: every paying tier
-- and every live trial can read the signal feed. Feed *breadth* (core vs full) is
-- enforced per-connection by the FastAPI WebSocket layer, not by RLS.
