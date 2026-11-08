-- Two fleets, one demo user each (password: halflife-demo), and placeholder
-- scores dated 2025-01-01 so the web app works before real scoring runs.
insert into fleets (id, name) values
  ('11111111-1111-1111-1111-111111111111', 'Acme Storage'),
  ('22222222-2222-2222-2222-222222222222', 'Northwind');

insert into auth.users (
  instance_id, id, aud, role, email, encrypted_password, email_confirmed_at,
  raw_app_meta_data, raw_user_meta_data, created_at, updated_at,
  confirmation_token, recovery_token, email_change_token_new, email_change
)
select '00000000-0000-0000-0000-000000000000', id, 'authenticated', 'authenticated', email,
  extensions.crypt('halflife-demo', extensions.gen_salt('bf')), now(),
  '{"provider":"email","providers":["email"]}', '{}', now(), now(), '', '', '', ''
from (values
  ('aaaaaaaa-0000-0000-0000-000000000001'::uuid, 'demo@acme.test'),
  ('bbbbbbbb-0000-0000-0000-000000000001'::uuid, 'demo@northwind.test')
) u(id, email);

insert into auth.identities (id, user_id, provider_id, identity_data, provider, created_at, updated_at)
select gen_random_uuid(), id, id::text, jsonb_build_object('sub', id::text, 'email', email),
  'email', now(), now()
from auth.users where email like 'demo@%';

-- Demo users have a public password, so they are viewers: they can read but not upload.
insert into memberships (user_id, fleet_id, role) values
  ('aaaaaaaa-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'viewer'),
  ('bbbbbbbb-0000-0000-0000-000000000001', '22222222-2222-2222-2222-222222222222', 'viewer');

insert into drives (fleet_id, drive_id, model, manufacturer, capacity_tb)
select f.id, 'SEED-' || left(f.name, 1) || lpad(i::text, 3, '0'), 'ST16000NM001G', 'Seagate', 16
from fleets f, generate_series(1, 20) i;

insert into drive_scores (fleet_id, drive_id, score_date, risk, rank, age_days, top_drivers, model_version)
select fleet_id, drive_id, date '2025-01-01', 1.0 / (row_number() over w + 1),
  row_number() over w, 900, '["Placeholder score from seed data"]', 'seed'
from drives window w as (partition by fleet_id order by drive_id);
