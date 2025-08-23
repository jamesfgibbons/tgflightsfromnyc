
import argparse
import os
import datetime as dt
from typing import List, Dict
from supabase import create_client

from ..config import settings

def _client():
    return create_client(settings.supabase_url, settings.supabase_service_role)

def _fetch_daily_min(n_days:int=7) -> List[Dict]:
    sb = _client()
    today = dt.date.today()
    start = today
    end = today + dt.timedelta(days=n_days-1)
    data = sb.table("caribbean_offers")\
        .select("dest_airport,date_depart,price_usd")\
        .gte("date_depart", str(start))\
        .lte("date_depart", str(end))\
        .execute().data
    by_key = {}
    for r in data or []:
        k = (r["dest_airport"], r["date_depart"])
        price = float(r["price_usd"])
        by_key[k] = min(by_key.get(k, 1e12), price)
    out = [{"dest_airport":k[0], "date_depart":k[1], "min_price":v} for k,v in by_key.items()]
    out.sort(key=lambda x:(x["dest_airport"], x["date_depart"]))
    return out

def _to_momentum(rows: List[Dict], duration_sec:int=45) -> Dict[str, Dict]:
    by_dest: Dict[str, List[Dict]] = {}
    for r in rows:
        by_dest.setdefault(r["dest_airport"], []).append(r)

    tracks = {}
    for dest, seq in by_dest.items():
        seq = sorted(seq, key=lambda x:x["date_depart"])
        if not seq:
            continue
        segs = []
        t = 0.0
        if len(seq) == 1:
            segs = [{"t0":0.0,"t1":duration_sec,"label":"neutral","score":0.0}]
        else:
            slot = duration_sec / max(1,len(seq)-1)
            for i in range(1, len(seq)):
                prev = seq[i-1]["min_price"]
                cur = seq[i]["min_price"]
                if prev == 0: prev = 1.0
                pct = (prev-cur)/prev  # drop -> positive
                if pct > 0.07:
                    label = "positive"; score = min(1.0, pct*4)
                elif pct < -0.07:
                    label = "negative"; score = max(-1.0, pct*4)
                else:
                    label = "neutral"; score = pct
                segs.append({"t0": round(t,2), "t1": round(t+slot,2), "label": label, "score": round(score,3)})
                t += slot

        tracks[dest] = {
            "region":"caribbean",
            "theme":"caribbean_kokomo",
            "job_key": f"nyc-{dest}-{dt.date.today().isoformat()}",
            "momentum": segs,
            "label_summary": {
                "positive_count": sum(1 for s in segs if s["label"]=="positive"),
                "negative_count": sum(1 for s in segs if s["label"]=="negative"),
                "neutral_count": sum(1 for s in segs if s["label"]=="neutral"),
            },
            "duration_sec": duration_sec,
            "sound_pack":"Tropical Pop"
        }
    return tracks

def run(n_days:int=7, duration:int=45):
    rows = _fetch_daily_min(n_days=n_days)
    tracks = _to_momentum(rows, duration_sec=duration)
    sb = _client()
    payload = list(tracks.values())
    if not payload:
        print("No tracks to write; did you load offers first?")
        return
    for i in range(0, len(payload), 200):
        batch = payload[i:i+200]
        sb.table("momentum_bands").insert(batch).execute()
    print(f"✅ Wrote {len(payload)} momentum_bands rows")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=int(os.getenv("DAYS","7")))
    ap.add_argument("--duration", type=int, default=45)
    args = ap.parse_args()
    run(n_days=args.days, duration=args.duration)
