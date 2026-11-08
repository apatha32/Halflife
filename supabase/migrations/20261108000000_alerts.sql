alter table drive_scores add column scored_at timestamptz not null default now();

create table alerts (
  fleet_id uuid not null references fleets on delete cascade,
  drive_id text not null,
  score_date date not null,
  kind text not null check (kind in ('entered_top_k', 'rank_jump')),
  rank int not null,
  prev_rank int,
  created_at timestamptz not null default now(),
  primary key (fleet_id, drive_id, score_date, kind)
);
alter table alerts enable row level security;
create policy member_read on alerts for select to authenticated using (is_member(fleet_id));

-- New alerts for one fleet and day versus the previous real scoring date.
-- A drive alerts when it enters the top k, or rises at least `jump` ranks into the top 10k.
-- Returns only rows it inserted, so re-running a day returns nothing.
create function make_alerts(fid uuid, day date, k int, jump int default 100)
returns setof alerts language sql as $$
  with prev as (
    select max(score_date) as d from drive_scores
    where fleet_id = fid and score_date < day and model_version <> 'seed'
  ), cur as (
    select s.drive_id, s.rank, p.rank as prev_rank
    from drive_scores s
    left join drive_scores p
      on p.fleet_id = s.fleet_id and p.drive_id = s.drive_id and p.score_date = (select d from prev)
    where s.fleet_id = fid and s.score_date = day and (select d from prev) is not null
  )
  insert into alerts (fleet_id, drive_id, score_date, kind, rank, prev_rank)
  select fid, drive_id, day,
    case when rank <= k and (prev_rank is null or prev_rank > k) then 'entered_top_k' else 'rank_jump' end,
    rank, prev_rank
  from cur
  where (rank <= k and (prev_rank is null or prev_rank > k))
     or (rank <= 10 * k and prev_rank - rank >= jump)
  on conflict do nothing
  returning *
$$;
revoke execute on function make_alerts from public, anon, authenticated;
