-- Best-Time to Book: schema + RPCs (idempotent)

-- Raw observations (optional if you already persist depart dates)
create table if not exists price_observation (
  id uuid primary key default gen_random_uuid(),
  captured_at timestamptz not null default now(),
  origin text not null,
  destination text not null,
  depart_date date not null,
  return_date date,
  cabin text not null default 'economy',
  stops int not null default 0,
  price_usd numeric not null,
  source text not null,
  meta jsonb default '{}'::jsonb
);

create index if not exists ix_obs_route_date on price_observation(origin, destination, depart_date);
create index if not exists ix_obs_captured on price_observation(captured_at desc);

-- Lead-time curve RPC (quantiles by lead days for a given month)
create or replace function lead_time_curve_fn(
  p_origin text, p_dest text, p_month int, p_cabin text default 'economy'
)
returns table (
  origin text, destination text, month int, cabin text,
  lead int, q10 numeric, q25 numeric, q50 numeric, q75 numeric,
  n int, volatility numeric, drop_prob numeric
) language sql stable as $$
with obs as (
  select origin, destination, cabin,
         (depart_date - current_date) as lead,
         extract(month from depart_date)::int as month,
         price_usd
  from price_observation
  where origin = p_origin
    and destination = p_dest
    and extract(month from depart_date)::int = p_month
    and (p_cabin is null or cabin = p_cabin)
    and depart_date >= current_date
),
agg as (
  select origin, destination, month, coalesce(p_cabin,'economy') as cabin,
         lead,
         count(*) as n,
         percentile_cont(0.10) within group (order by price_usd) as q10,
         percentile_cont(0.25) within group (order by price_usd) as q25,
         percentile_cont(0.50) within group (order by price_usd) as q50,
         percentile_cont(0.75) within group (order by price_usd) as q75
  from obs
  group by origin, destination, month, lead
)
select origin, destination, month, cabin, lead, q10, q25, q50, q75, n,
       null::numeric as volatility,
       null::numeric as drop_prob
from agg
order by lead;
$$;

-- Summary RPC: BWI, sweet-spot window, recommendation
create or replace function best_time_summary_fn(
  p_origin text, p_dest text, p_month int, p_cabin text default 'economy'
)
returns table (
  origin text, destination text, month int, cabin text,
  bwi int, sweet_spot_start int, sweet_spot_end int,
  today_price numeric, delta_pct numeric,
  rec text, confidence int, rationale text
) language plpgsql stable as $$
declare
  min_q50 numeric;
  p75 numeric;
  t_q50 numeric;
  start_lead int;
  end_lead int;
begin
  with c as (
    select * from lead_time_curve_fn(p_origin, p_dest, p_month, p_cabin)
  ), mins as (
    select min(q50) as min_q50,
           percentile_cont(0.75) within group (order by q50) as p75
    from c where n >= 5
  ), sweet as (
    select min(lead) as start_lead, max(lead) as end_lead
    from c, mins where c.q50 <= mins.min_q50 * 1.05 and c.n >= 5
  ), today as (
    select q50 from c where lead >= 0 order by lead limit 1
  )
  select mins.min_q50, mins.p75, sweet.start_lead, sweet.end_lead, today.q50
  into min_q50, p75, start_lead, end_lead, t_q50
  from mins, sweet, today;

  if min_q50 is null or t_q50 is null then
    return query select p_origin, p_dest, p_month, coalesce(p_cabin,'economy'),
      50, 45, 75, null::numeric, null::numeric, 'TRACK', 50,
      'Insufficient data; track for a better window.';
    return;
  end if;

  if p75 is null or p75 <= min_q50 then
    p75 := min_q50 * 1.25;
  end if;

  return query
  select p_origin, p_dest, p_month, coalesce(p_cabin,'economy'),
         greatest(0, least(100, round(100 * (1 - (t_q50 - min_q50) / nullif(p75 - min_q50,0)))))::int as bwi,
         coalesce(start_lead, 45), coalesce(end_lead, 75),
         t_q50, null::numeric,
         case when t_q50 <= min_q50 * 1.10 then 'BUY'
              when t_q50 <= min_q50 * 1.30 then 'TRACK'
              else 'WAIT' end,
         70,
         'Recommendation based on median vs sweet‑spot and interquartile spread.';
end;
$$;

