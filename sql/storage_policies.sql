-- Storage bucket setup and policies for Option A (public read-only assets)

-- Buckets (idempotent upserts)
insert into storage.buckets (id, name, public)
values ('serpradio-artifacts', 'serpradio-artifacts', false)
on conflict (id) do update set public = excluded.public;

insert into storage.buckets (id, name, public)
values ('serpradio-public', 'serpradio-public', true)
on conflict (id) do update set public = excluded.public;

-- Ensure RLS is enabled (it is by default on storage.objects in Supabase)
-- alter table storage.objects enable row level security; -- usually already enabled

-- Public read for the public bucket (anon + authenticated)
create policy if not exists "Public read access (serpradio-public)"
on storage.objects for select
to public
using (bucket_id = 'serpradio-public');

-- Optional: Allow no client writes by default. Writes occur via service role in backend only.
-- If client uploads are desired later, add narrowly scoped insert/update policies with path prefixes.

