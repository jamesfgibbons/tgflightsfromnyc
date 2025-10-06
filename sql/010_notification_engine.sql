-- Notification Engine (events + board badges)

create table if not exists notification_events (
  id uuid primary key default gen_random_uuid(),
  origin text not null,
  dest text not null,
  event_type text not null,
  severity text not null default 'info',
  delta_pct numeric,
  zscore numeric,
  today_price numeric,
  window_start date,
  window_end date,
  observed_at timestamptz not null default now(),
  meta jsonb default '{}'::jsonb
);

create index if not exists ix_notif_route_time on notification_events(origin, dest, observed_at desc);

create materialized view if not exists board_badges_live as
select origin, dest,
       max(observed_at) as last_seen,
       max(case when event_type='price_drop' then delta_pct end) as drop_pct,
       bool_or(event_type='window_open') as window_open,
       max(severity) filter (where event_type in ('price_drop','price_spike')) as top_severity
from notification_events
where observed_at >= now() - interval '24 hours'
group by origin, dest;

-- Optional pg_cron job (uncomment and adjust if pg_cron is enabled)
-- select cron.schedule(
--   'emit-notifications-6h',
--   '0 */6 * * *',
--   $$
--   -- Example logic: compare today price vs 30d median to emit events
--   with latest as (
--     select origin, destination as dest,
--            avg(price_usd) filter (where day = current_date) as today,
--            percentile_cont(0.5) within group (order by price_usd) filter (where day>=current_date-30) as p50_30d
--     from price_quotes_daily
--     group by 1,2
--   )
--   insert into notification_events (origin, dest, event_type, severity, delta_pct, today_price, meta)
--   select origin, dest,
--          case when ((today - p50_30d)/nullif(p50_30d,0)) <= -0.1 then 'price_drop'
--               when ((today - p50_30d)/nullif(p50_30d,0)) >=  0.1 then 'price_spike'
--               else 'trend_reversal' end as event_type,
--          case when ((today - p50_30d)/nullif(p50_30d,0)) <= -0.2 then 'urgent'
--               when ((today - p50_30d)/nullif(p50_30d,0)) <= -0.1 then 'alert'
--               else 'info' end as severity,
--          round(100 * (today - p50_30d)/nullif(p50_30d,0), 1) as delta_pct,
--          today,
--          jsonb_build_object('p50_30d', p50_30d)
--   from latest
--   where today is not null and p50_30d is not null
--   $$);

