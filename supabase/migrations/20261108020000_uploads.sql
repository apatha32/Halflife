-- Customer uploads: admins of a fleet upload a CSV, review the proposed column mapping,
-- and approve it; the worker (service role) does everything else.
alter table memberships add column role text not null default 'admin'
  check (role in ('admin', 'viewer'));

create function is_admin(fid uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.memberships
    where user_id = auth.uid() and fleet_id = fid and role = 'admin'
  )
$$;

create table uploads (
  id uuid primary key default gen_random_uuid(),
  fleet_id uuid not null references fleets on delete cascade,
  path text not null unique,
  filename text not null,
  status text not null default 'uploaded'
    check (status in ('uploaded', 'needs_review', 'approved', 'processing', 'scored', 'failed')),
  mapping jsonb,
  result jsonb,
  error text,
  created_by uuid default auth.uid(),
  created_at timestamptz not null default now()
);
alter table uploads enable row level security;
create policy member_read on uploads for select to authenticated using (is_member(fleet_id));
create policy admin_insert on uploads for insert to authenticated
  with check (is_admin(fleet_id) and status = 'uploaded' and path like fleet_id::text || '/%');
create policy admin_review on uploads for update to authenticated
  using (is_admin(fleet_id) and status = 'needs_review')
  with check (status in ('needs_review', 'approved'));
-- Users may only name the file on insert and edit the mapping / approve on update.
revoke insert, update on uploads from authenticated;
grant insert (fleet_id, path, filename) on uploads to authenticated;
grant update (mapping, status) on uploads to authenticated;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('uploads', 'uploads', false, 20971520, array['text/csv']);
create policy upload_insert on storage.objects for insert to authenticated
  with check (bucket_id = 'uploads' and public.is_admin(((storage.foldername(name))[1])::uuid));
create policy upload_read on storage.objects for select to authenticated
  using (bucket_id = 'uploads' and public.is_member(((storage.foldername(name))[1])::uuid));
