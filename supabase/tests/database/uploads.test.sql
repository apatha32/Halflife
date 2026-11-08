begin;
select plan(7);

-- Make the Northwind demo user an admin inside this test only.
update memberships set role = 'admin' where user_id = 'bbbbbbbb-0000-0000-0000-000000000001';

set local role authenticated;
set local request.jwt.claims = '{"sub": "aaaaaaaa-0000-0000-0000-000000000001"}';
select throws_ok($$insert into uploads (fleet_id, path, filename) values
  ('11111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111/a.csv', 'a.csv')$$,
  '42501', null, 'a viewer cannot upload');

set local request.jwt.claims = '{"sub": "bbbbbbbb-0000-0000-0000-000000000001"}';
select lives_ok($$insert into uploads (fleet_id, path, filename) values
  ('22222222-2222-2222-2222-222222222222', '22222222-2222-2222-2222-222222222222/n.csv', 'n.csv')$$,
  'an admin uploads to its own fleet');
select throws_ok($$insert into uploads (fleet_id, path, filename) values
  ('11111111-1111-1111-1111-111111111111', '11111111-1111-1111-1111-111111111111/x.csv', 'x.csv')$$,
  '42501', null, 'an admin cannot upload to another fleet');
select throws_ok($$update uploads set path = 'elsewhere' where filename = 'n.csv'$$,
  '42501', null, 'users cannot change the file path');

reset role;
update uploads set status = 'needs_review' where filename = 'n.csv';
set local role authenticated;
set local request.jwt.claims = '{"sub": "bbbbbbbb-0000-0000-0000-000000000001"}';
update uploads set status = 'approved', mapping = '{"columns": {}}' where filename = 'n.csv';
select is((select status from uploads where filename = 'n.csv'), 'approved', 'an admin approves a mapping under review');
update uploads set status = 'scored' where filename = 'n.csv';
select is((select status from uploads where filename = 'n.csv'), 'approved', 'users cannot mark an upload scored');

set local request.jwt.claims = '{"sub": "aaaaaaaa-0000-0000-0000-000000000001"}';
select is((select count(*) from uploads where filename = 'n.csv'), 0::bigint, 'other fleets cannot see the upload');

select * from finish();
rollback;
