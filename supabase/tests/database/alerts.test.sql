begin;
select plan(6);

insert into drives (fleet_id, drive_id) select '11111111-1111-1111-1111-111111111111', d
  from unnest(array['A', 'B', 'C', 'D', 'E']) d;
insert into drive_scores (fleet_id, drive_id, score_date, risk, rank, model_version) values
  ('11111111-1111-1111-1111-111111111111', 'A', '2025-12-01', .9, 1, 'v'),
  ('11111111-1111-1111-1111-111111111111', 'B', '2025-12-01', .5, 3, 'v'),
  ('11111111-1111-1111-1111-111111111111', 'C', '2025-12-01', .1, 400, 'v'),
  ('11111111-1111-1111-1111-111111111111', 'E', '2025-12-01', .2, 300, 'v'),
  ('11111111-1111-1111-1111-111111111111', 'A', '2025-12-02', .9, 1, 'v'),
  ('11111111-1111-1111-1111-111111111111', 'B', '2025-12-02', .5, 5, 'v'),
  ('11111111-1111-1111-1111-111111111111', 'C', '2025-12-02', .8, 2, 'v'),
  ('11111111-1111-1111-1111-111111111111', 'D', '2025-12-02', .7, 3, 'v'),
  ('11111111-1111-1111-1111-111111111111', 'E', '2025-12-02', .3, 15, 'v');

select is((select count(*) from make_alerts('11111111-1111-1111-1111-111111111111', '2025-12-01', 2)), 0::bigint,
  'no alerts without a previous real scoring date (seed ignored)');
select results_eq(
  $$select drive_id, kind, rank, prev_rank from make_alerts('11111111-1111-1111-1111-111111111111', '2025-12-02', 2) order by 1$$,
  $$values ('C', 'entered_top_k', 2, 400), ('E', 'rank_jump', 15, 300)$$,
  'C entered the top 2, E jumped 285 ranks; nothing for A (already in), B (dropped) or D (new, outside top 2)');
select is((select count(*) from make_alerts('11111111-1111-1111-1111-111111111111', '2025-12-02', 2)), 0::bigint,
  're-running a day creates no duplicate alerts');

set local role authenticated;
set local request.jwt.claims = '{"sub": "bbbbbbbb-0000-0000-0000-000000000001"}';
select is((select count(*) from alerts), 0::bigint, 'Northwind user reads no Acme alerts');
select throws_ok($$select make_alerts('11111111-1111-1111-1111-111111111111', '2025-12-02', 2)$$,
  '42501', null, 'signed-in users cannot run make_alerts');
set local request.jwt.claims = '{"sub": "aaaaaaaa-0000-0000-0000-000000000001"}';
select is((select count(*) from alerts), 2::bigint, 'Acme user reads its alerts');

select * from finish();
rollback;
