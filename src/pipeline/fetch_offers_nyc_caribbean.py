import os, time, datetime as dt
from typing import List
from supabase import create_client
from tqdm import tqdm

from src.config import settings
from src.geo_registry import NYC_AIRPORTS, CARIBBEAN_AIRPORTS
from src.providers.flights_provider import search_one_day

def upsert_offers(sb, rows: List[dict]):
    if not rows: return 0
    # Upsert in chunks of 500
    total = 0
    for i in range(0, len(rows), 500):
        chunk = rows[i:i+500]
        sb.table("flight_offers").upsert(chunk, on_conflict="offer_id").execute()
        total += len(chunk)
    return total

def run(days: int=14, nonstop_only: bool=True, throttle: float=0.4):
    settings.assert_minimum()
    sb = create_client(settings.supabase_url, settings.supabase_key)

    today = dt.date.today()
    for d in range(days):
        date_iso = (today + dt.timedelta(days=d)).isoformat()
        batch = []
        for orig in NYC_AIRPORTS:
            for dest in CARIBBEAN_AIRPORTS:
                try:
                    for offer in search_one_day(orig, dest, date_iso, nonstop_only):
                        batch.append(offer)
                except Exception as e:
                    print(f"WARN {orig}->{dest} {date_iso}: {e}")
                time.sleep(throttle)  # rate limit
        n = upsert_offers(sb, batch)
        print(f"🛬 {date_iso}: upserted {n} offers")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--nonstop-only", action="store_true")
    ap.add_argument("--throttle", type=float, default=0.4)
    args = ap.parse_args()
    run(days=args.days, nonstop_only=args.nonstop_only, throttle=args.throttle)
