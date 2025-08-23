import os, time, datetime as dt
from supabase import create_client
from src.providers.flights_provider import search_one_day
from src.pipeline.geo_registry import NYC_AIRPORTS, CARIBBEAN_AIRPORTS

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE"])

def upsert_offers(rows):
    if not rows: return
    for i in range(0, len(rows), 500):
        chunk = rows[i:i+500]
        sb.table("flight_offers").upsert(chunk, on_conflict="offer_id").execute()

def run(days=14, nonstop_only=True, throttle=0.6):
    today = dt.date.today()
    for d in range(days):
        date_iso = (today + dt.timedelta(days=d)).isoformat()
        batch=[]
        for orig in NYC_AIRPORTS:
            for dest in CARIBBEAN_AIRPORTS:
                try:
                    for offer in search_one_day(orig, dest, date_iso, nonstop_only):
                        batch.append(offer)
                except Exception as e:
                    print("WARN", orig, dest, date_iso, str(e))
                time.sleep(throttle)  # rate limit
        upsert_offers(batch)
        print(f"🛬 {date_iso}: upserted {len(batch)} offers")

if __name__ == "__main__":
    run()