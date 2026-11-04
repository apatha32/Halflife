create table fleets (
  id uuid primary key default gen_random_uuid(),
  name text not null unique
);

create table memberships (
  user_id uuid not null references auth.users on delete cascade,
  fleet_id uuid not null references fleets on delete cascade,
  primary key (user_id, fleet_id)
);

create table drives (
  fleet_id uuid not null references fleets on delete cascade,
  drive_id text not null,
  model text,
  manufacturer text,
  capacity_tb real,
  primary key (fleet_id, drive_id)
);

create table drive_scores (
  fleet_id uuid not null,
  drive_id text not null,
  score_date date not null,
  risk real not null,
  rank int not null,
  age_days real,
  coverage real not null default 1,
  top_drivers jsonb not null default '[]',
  model_version text not null,
  primary key (fleet_id, drive_id, score_date),
  foreign key (fleet_id, drive_id) references drives on delete cascade
);
create index on drive_scores (fleet_id, score_date, rank);

create table drive_history (
  fleet_id uuid not null,
  drive_id text not null,
  date date not null,
  smart_5 bigint,
  smart_187 bigint,
  smart_197 bigint,
  smart_198 bigint,
  smart_194 bigint,
  primary key (fleet_id, drive_id, date),
  foreign key (fleet_id, drive_id) references drives on delete cascade
);

create table quality_reports (
  fleet_id uuid not null references fleets on delete cascade,
  run_at timestamptz not null,
  report jsonb not null,
  primary key (fleet_id, run_at)
);

create function is_member(fid uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.memberships where user_id = auth.uid() and fleet_id = fid
  )
$$;

alter table fleets enable row level security;
alter table memberships enable row level security;
alter table drives enable row level security;
alter table drive_scores enable row level security;
alter table drive_history enable row level security;
alter table quality_reports enable row level security;

create policy member_read on fleets for select to authenticated using (is_member(id));
create policy own_read on memberships for select to authenticated using (user_id = auth.uid());
create policy member_read on drives for select to authenticated using (is_member(fleet_id));
create policy member_read on drive_scores for select to authenticated using (is_member(fleet_id));
create policy member_read on drive_history for select to authenticated using (is_member(fleet_id));
create policy member_read on quality_reports for select to authenticated using (is_member(fleet_id));

create function pull_list(fid uuid, k int default 50)
returns table (
  drive_id text, model text, age_days real, risk real, rank int,
  top_driver text, coverage real, score_date date
)
language sql stable security invoker as $$
  select s.drive_id, d.model, s.age_days, s.risk, s.rank,
         s.top_drivers ->> 0, s.coverage, s.score_date
  from drive_scores s join drives d using (fleet_id, drive_id)
  where s.fleet_id = fid
    and s.score_date = (select max(score_date) from drive_scores where fleet_id = fid)
  order by s.rank
  limit k
$$;
