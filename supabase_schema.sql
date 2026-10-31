create table if not exists public.events (
  id text primary key,
  event_name text not null,
  event_date text,
  city text,
  platform text not null,
  url text not null,
  target_price numeric,
  currency text default 'USD',
  created_at timestamptz default now()
);

create table if not exists public.snapshots (
  id text primary key,
  event_id text not null references public.events(id) on delete cascade,
  price numeric not null,
  currency text,
  platform text,
  section text,
  notes text,
  checked_at timestamptz
);

create table if not exists public.alerts (
  id text primary key,
  event_id text references public.events(id) on delete cascade,
  price numeric,
  message text,
  email_sent boolean default false,
  created_at timestamptz
);

-- MVP uses a single-owner app. Do not expose the database key publicly.
-- Configure RLS and per-user authentication before inviting other users.
alter table public.events enable row level security;
alter table public.snapshots enable row level security;
alter table public.alerts enable row level security;

-- For the personal MVP, use the Supabase service_role key only in Streamlit
-- server-side secrets, never in browser code or a public repository.
-- Service role bypasses RLS; do not share your app URL unless APP_PASSWORD is set.
