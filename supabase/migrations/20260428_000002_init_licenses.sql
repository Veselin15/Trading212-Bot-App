-- Trading212 Bot App (Supabase)
-- Licenses: portal-managed key for desktop executor.

create extension if not exists "pgcrypto";

create table if not exists public.licenses (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,

  license_key uuid not null unique default gen_random_uuid(),
  status text not null default 'active',

  revoked_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists licenses_user_id_idx on public.licenses (user_id);
create index if not exists licenses_status_idx on public.licenses (status);

drop trigger if exists licenses_set_updated_at on public.licenses;
create trigger licenses_set_updated_at
before update on public.licenses
for each row execute function public.set_updated_at();

alter table public.licenses enable row level security;

-- Users can read their own license(s) (useful for displaying in the portal).
drop policy if exists licenses_select_own on public.licenses;
create policy licenses_select_own
on public.licenses
for select
to authenticated
using (user_id = auth.uid());

-- Disallow all client-side writes. (Service role bypasses RLS.)
drop policy if exists licenses_no_insert on public.licenses;
create policy licenses_no_insert
on public.licenses
for insert
to authenticated
with check (false);

drop policy if exists licenses_no_update on public.licenses;
create policy licenses_no_update
on public.licenses
for update
to authenticated
using (false)
with check (false);

drop policy if exists licenses_no_delete on public.licenses;
create policy licenses_no_delete
on public.licenses
for delete
to authenticated
using (false);

