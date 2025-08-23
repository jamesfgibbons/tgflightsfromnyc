import datetime as dt
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from supabase import create_client
from src.config import settings
from src.geo_registry import CARIBBEAN_AIRPORTS

def _percentiles(vals: List[float]) -> Tuple[float,float,float,float,float]:
    if not vals: return (None,None,None,None,None)
    a = np.array(vals, dtype=float)
    return (float(np.min(a)), float(np.percentile(a,25)),
            float(np.median(a)), float(np.percentile(a,75)),
            float(np.max(a)))

def _sov_brand(df: pd.DataFrame) -> Dict[str, float]:
    # Share-of-voice by seller among cheapest half of offers
    if df.empty: return {}
    cutoff = df["price_usd"].median()
    cheap = df[df["price_usd"] <= cutoff]
    counts = cheap["seller_name"].value_counts(normalize=True)
    return {k: float(v) for k,v in counts.items()}

def compute_visibility_rows(sb, start: dt.date, days: int=14) -> List[dict]:
    rows = []
    end = start + dt.timedelta(days=days-1)
    resp = sb.table("flight_offers").select("*", count="exact").gte("date_depart", str(start)).lte("date_depart", str(end)).execute()
    data = resp.data or []
    if not data: return rows
    df = pd.DataFrame(data)
    # Guard columns
    for col in ["origin_metro","dest_airport","date_depart","price_usd","seller_name"]:
        if col not in df.columns:
            return rows
    # Filter Caribbean
    df = df[df["dest_airport"].isin(CARIBBEAN_AIRPORTS)]
    df["date_depart"] = pd.to_datetime(df["date_depart"]).dt.date
    groups = df.groupby(["origin_metro","dest_airport","date_depart"], as_index=False)
    for (metro,dest,day), g in groups:
        prices = g["price_usd"].tolist()
        pmin,p25,p50,p75,pmax = _percentiles(prices)
        vol = float(np.std(prices)) if len(prices) >= 3 else 0.0
        sov = _sov_brand(g)
        rows.append({
            "region": "caribbean",
            "origin": metro,
            "destination": dest,
            "date_bucket": str(day),
            "price_min": pmin,
            "price_p25": p25,
            "price_median": p50,
            "price_p75": p75,
            "price_max": pmax,
            "volatility": vol,
            "sov_brand": sov,
            "sample_size": int(len(prices)),
            "src": "offers_etl"
        })
    return rows

def upsert_visibility(sb, rows: List[dict]) -> int:
    if not rows: return 0
    total = 0
    for i in range(0, len(rows), 500):
        sb.table("flight_visibility").upsert(rows[i:i+500],
            on_conflict="region,origin,destination,date_bucket").execute()
        total += len(rows[i:i+500])
    return total

def run(days: int=14):
    settings.assert_minimum()
    sb = create_client(settings.supabase_url, settings.supabase_key)
    start = dt.date.today()
    rows = compute_visibility_rows(sb, start, days=days)
    n = upsert_visibility(sb, rows)
    print(f"📊 flight_visibility upserted rows: {n}")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    args = ap.parse_args()
    run(days=args.days)
