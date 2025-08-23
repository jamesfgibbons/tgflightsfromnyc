import os, json, math, hashlib, datetime as dt
from supabase import create_client

SB = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE"])

def sha(s:str)->str: return hashlib.sha256(s.encode()).hexdigest()

def aggregate_visibility(region:str="caribbean", days:int=7):
    # Pull winners for last N days and compute summary stats for flight_visibility
    today = dt.date.today()
    start = today - dt.timedelta(days=days)
    winners = SB.rpc("execute_sql", {"sql": """
      select f.origin_airport as origin, f.dest_airport as destination, f.date_depart::date as d,
             min(price_usd) as price_min,
             percentile_cont(0.25) within group (order by price_usd) as p25,
             percentile_cont(0.50) within group (order by price_usd) as p50,
             percentile_cont(0.75) within group (order by price_usd) as p75,
             max(price_usd) as price_max,
             count(*) as n
      from flight_offers f
      where lower(f.dest_region) = %s and f.date_depart between %s and %s
      group by 1,2,3
      order by 3 asc
    ""","args":[region, start.isoformat(), today.isoformat()]}).execute()
    rows = winners.data if hasattr(winners,"data") else []
    vis=[]
    for r in rows:
        p25 = r["p25"] or None; p50 = r["p50"] or None; p75 = r["p75"] or None
        volatility = None
        if p25 and p75 and p50 and p50>0:
            volatility = (p75 - p25) / p50
        vis.append({
          "region": region, "origin": r["origin"], "destination": r["destination"],
          "date_bucket": r["d"], "price_min": r["price_min"], "price_p25": p25,
          "price_median": p50, "price_p75": p75, "price_max": r["price_max"],
          "volatility": volatility, "sov_brand": None, "sample_size": r["n"]
        })
    for i in range(0,len(vis),500):
        SB.table("flight_visibility").upsert(vis[i:i+500],
          on_conflict="region,origin,destination,date_bucket").execute()
    print(f"Cached {len(vis)} visibility rows for region={region}.")

def momentum_from_stats(price_min, price_median, price_p75, volatility):
    # Simple rules -> 30–60s track with 4 segments
    dur = 45
    seg = dur/4
    # Translate stats to sentiment signals
    pos = 0.6 if (price_min and price_median and price_min <= 0.85*price_median) else 0.2
    neg = -0.6 if (volatility and volatility >= 0.35) else -0.2
    return dur, [
      {"t0":0.0, "t1":seg,    "label":"positive","score":pos},
      {"t0":seg, "t1":2*seg,  "label":"neutral", "score":0.1},
      {"t0":2*seg,"t1":3*seg, "label":"positive","score":pos+0.15},
      {"t0":3*seg,"t1":dur,   "label":"negative","score":neg},
    ]

def seed_momentum(region:str="caribbean", theme:str="caribbean_kokomo"):
    # Turn today's cheapest per destination (NYC) into momentum_bands
    today = dt.date.today().isoformat()
    rb = SB.rpc("execute_sql", {"sql": """
      select m.dest_airport, m.min_price_usd
      from v_daily_min_by_metro m
      where m.origin_metro='NYC' and m.date_depart = current_date
    ""","args":[]}).execute()
    rows = rb.data if hasattr(rb,"data") else []
    entries=[]
    for r in rows:
        dur, mom = momentum_from_stats(price_min=r["min_price_usd"], price_median=r["min_price_usd"]*1.12,
                                       price_p75=r["min_price_usd"]*1.25, volatility=0.2)
        entry = {
          "region": region,
          "theme": theme,
          "job_key": f"nyc-{r['dest_airport']}-{today}",
          "momentum": mom,
          "label_summary": {
            "positive_count": sum(1 for x in mom if x["label"]=="positive"),
            "negative_count": sum(1 for x in mom if x["label"]=="negative"),
            "neutral_count":  sum(1 for x in mom if x["label"]=="neutral")
          },
          "duration_sec": dur,
          "sound_pack": "Tropical Pop"
        }
        entries.append(entry)
    for i in range(0,len(entries),500):
        SB.table("momentum_bands").upsert(entries[i:i+500], on_conflict="job_key").execute()
    print(f"Seeded {len(entries)} Kokomo momentum entries for today.")

def run():
    aggregate_visibility(region="caribbean", days=7)
    seed_momentum(region="caribbean", theme="caribbean_kokomo")

if __name__ == "__main__":
    run()