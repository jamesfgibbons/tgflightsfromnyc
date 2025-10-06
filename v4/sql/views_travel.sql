create or replace view vw_latest_price_quotes as
select distinct on (origin, destination)
  origin,
  destination,
  window_days,
  price_low_usd,
  price_high_usd,
  typical_airlines,
  cited_websites,
  brands,
  notes,
  created_at
from price_quotes
order by origin, destination, created_at desc;
