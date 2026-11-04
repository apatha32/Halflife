begin;
select plan(4);

set local role authenticated;
set local request.jwt.claims = '{"sub": "aaaaaaaa-0000-0000-0000-000000000001"}';

select is((select count(*) from drive_scores where fleet_id = '22222222-2222-2222-2222-222222222222'), 0::bigint,
  'Acme user reads zero Northwind scores');
select ok((select count(*) from drive_scores) > 0, 'Acme user reads Acme scores');
select is((select count(*) from pull_list('22222222-2222-2222-2222-222222222222', 50)), 0::bigint,
  'pull_list respects RLS');
select is((select count(*) from fleets), 1::bigint, 'Acme user sees only its fleet');

select * from finish();
rollback;
