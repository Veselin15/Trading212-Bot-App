-- Trading212 Bot App (Supabase)
-- Add fields needed for backend WS license enforcement.

do $$
begin
  -- expires_at is optional; if null, subscription gating controls access.
  if not exists (
    select 1
    from information_schema.columns
    where table_schema = 'public' and table_name = 'licenses' and column_name = 'expires_at'
  ) then
    alter table public.licenses add column expires_at timestamptz;
  end if;

  if not exists (
    select 1
    from information_schema.columns
    where table_schema = 'public' and table_name = 'licenses' and column_name = 'last_ip_address'
  ) then
    alter table public.licenses add column last_ip_address inet;
  end if;

  if not exists (
    select 1
    from information_schema.columns
    where table_schema = 'public' and table_name = 'licenses' and column_name = 'last_seen_at'
  ) then
    alter table public.licenses add column last_seen_at timestamptz;
  end if;
end $$;

create index if not exists licenses_last_seen_at_idx on public.licenses (last_seen_at desc);

