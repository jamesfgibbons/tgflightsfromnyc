-- Helpful view: quick Caribbean slice
create or replace view vw_caribbean_visibility as
select * from flight_visibility where lower(region) = 'caribbean';

-- Ensure public read access to the view
-- (Run these in Supabase SQL Editor after creating the view)
-- grant select on vw_caribbean_visibility to anon;
-- grant select on vw_caribbean_visibility to authenticated;