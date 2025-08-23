import os, json, hashlib
from typing import List, Dict, Any
from supabase import create_client
from openai import OpenAI

SB = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE"])
OA = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

SCHEMA = {
  "type":"object",
  "properties":{
    "brand_seller":{"type":"string"},
    "seller_type":{"type":"string","enum":["airline","OTA","meta","unknown"]},
    "routing":{"type":"string","enum":["direct","connecting","red_eye","positioning","unknown"]},
    "novelty_score":{"type":"number","minimum":0,"maximum":10},
    "novelty_reasons":{"type":"array","items":{"type":"string"}},
    "kokomo_hint":{"type":"string","description":"steel_drums|marimba|wind_chimes|''"}
  },
  "required":["brand_seller","seller_type","routing","novelty_score","novelty_reasons","kokomo_hint"],
  "additionalProperties": False
}

def key_for(row:Dict[str,Any])->str:
    base = json.dumps({
      "seller":row["seller_name"],"carrier":row["carrier_name"],
      "origin":row["origin_airport"],"dest":row["dest_airport"],
      "date":row["date_depart"],"time_window":row["time_window"],
      "nonstop":row["nonstop"],"stops":row["stops"],"price":row["price_usd"],
      "region":row["dest_region"]
    }, sort_keys=True)
    return hashlib.sha256(base.encode()).hexdigest()

def enrich_offers(offers:List[Dict[str,Any]]):
    if not offers: return []

    msgs=[{"role":"system","content":"Classify flight offers. JSON only."}]
    for r in offers:
        msgs.append({"role":"user","content": json.dumps({
            "seller": r["seller_name"], "carrier": r["carrier_name"],
            "origin_airport": r["origin_airport"], "dest_airport": r["dest_airport"],
            "date_depart": r["date_depart"], "time_window": r["time_window"],
            "nonstop": r["nonstop"], "stops": r["stops"], "price_usd": r["price_usd"],
            "dest_region": r["dest_region"]
        })})
    resp = OA.responses.create(
        model="gpt-4o-mini",
        input=msgs,
        response_format={"type":"json_schema","json_schema":{"name":"BrandNovelty","schema":SCHEMA}},
        temperature=0.2
    )
    parsed = json.loads(resp.output_text)
    # If the model returns a list, map 1:1; if dict keyed, adapt gracefully.
    results = parsed if isinstance(parsed, list) else [parsed]
    out=[]
    for r,enr in zip(offers, results):
        out.append({
          "enrich_key": key_for(r),
          "offer_id": r["offer_id"],
          "model": "gpt-4o-mini",
          "response": enr
        })
    return out

def run(limit_per_day:int=200):
    # Take **winners** only to save cost: join flight_offers to v_daily_min_by_metro
    # NOTE: Supabase python client cannot query views with RPC easily in strict mode; we fetch winners via SQL REST:
    winners = SB.rpc("execute_sql", {"sql": """
      select f.*
      from flight_offers f
      join v_daily_min_by_metro m
        on m.origin_metro = f.origin_metro
       and m.dest_airport = f.dest_airport
       and m.date_depart = f.date_depart
       and f.price_usd = m.min_price_usd
      order by f.date_depart asc
      limit %s
    ""","args":[limit_per_day]}).execute()  # If you don't have RPC helper, pull recent rows via table filters instead.

    rows = winners.data if hasattr(winners,"data") else []
    if not rows:
        print("No winners found to enrich.")
        return

    enriched = enrich_offers(rows)
    # Write into cache_jobs as 'succeeded' and optionally into a small table 'llm_cache_responses'
    jobs = []
    for e in enriched:
        jobs.append({
          "prompt_key": e["enrich_key"],
          "prompt_hash": e["enrich_key"],
          "model": e["model"],
          "status": "succeeded",
          "payload": e["response"]
        })
    for i in range(0,len(jobs),500):
        SB.table("cache_jobs").upsert(jobs[i:i+500], on_conflict="prompt_hash").execute()
    print(f"Enriched {len(enriched)} winners.")

if __name__ == "__main__":
    run()