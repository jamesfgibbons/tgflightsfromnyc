import os, json, datetime as dt
from typing import List, Dict
from supabase import create_client
from src.config import settings
from .openai_client import FlightLLM

SYSTEM = (
  "You enrich flight visibility summaries. Return strict JSON for fields: "
  "brand_seller, seller_type (airline|OTA|meta|unknown), routing (direct|connecting|red_eye|positioning|unknown), "
  "novelty_score (0..10), novelty_reasons [strings], kokomo_hint (steel_drums|marimba|wind_chimes|none)."
)

def _mk_prompt(v: dict) -> Dict:
    return {
      "role": "user",
      "content": json.dumps({
        "region": v["region"], "origin": v["origin"], "destination": v["destination"],
        "date_bucket": v["date_bucket"],
        "price_min": v.get("price_min"), "price_median": v.get("price_median"),
        "volatility": v.get("volatility"),
        "sov_brand": v.get("sov_brand",{}),
        "notes": "Caribbean theme uses Tropical Pop; red-eye gets lower tempo.",
      })
    }

def run(days: int=7):
    settings.assert_minimum()
    sb = create_client(settings.supabase_url, settings.supabase_key)
    llm = FlightLLM()

    start = dt.date.today()
    end = start + dt.timedelta(days=days-1)
    res = sb.table("flight_visibility").select("*").gte("date_bucket", str(start)).lte("date_bucket", str(end)).eq("region","caribbean").execute()
    items: List[dict] = res.data or []
    if not items:
        print("No visibility rows found; run build_visibility first")
        return

    enriched_rows = []
    for v in items:
        # Use wrapper to get strict JSON
        out = llm.analyze_prompt(json.dumps({
            "task": "enrich_flight_visibility",
            "system": SYSTEM,
            "payload": {
                "region": v["region"], "origin": v["origin"], "destination": v["destination"],
                "date_bucket": v["date_bucket"],
                "price_min": v.get("price_min"), "price_median": v.get("price_median"),
                "volatility": v.get("volatility"),
                "sov_brand": v.get("sov_brand",{}),
            }
        }))
        enriched_rows.append({
            "region": v["region"],
            "origin": v["origin"],
            "destination": v["destination"],
            "date_bucket": v["date_bucket"],
            "brand_seller": out.get("brand_seller","Unknown"),
            "seller_type": out.get("seller_type","unknown"),
            "routing": out.get("routing","unknown"),
            "novelty_score": out.get("novelty_score",0),
            "novelty_reasons": out.get("novelty_reasons",[]),
            "kokomo_hint": out.get("kokomo_hint","none"),
        })

    # Store into a dedicated table for enrichment (create if not exists)
    for i in range(0, len(enriched_rows), 500):
        sb.table("visibility_enrichment").upsert(enriched_rows[i:i+500],
            on_conflict="region,origin,destination,date_bucket").execute()
    print(f"✨ Enriched rows: {len(enriched_rows)}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args()
    run(days=args.days)
