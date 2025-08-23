import json, math, datetime as dt
from typing import List, Dict
from supabase import create_client
from src.config import settings

def to_momentum_row(v: dict, e: dict) -> dict:
    # Map price drop/volatility/novelty into {t0,t1,label,score} segments
    # 45s track broken into 6s segments
    duration = 45
    seg_len = 6.0
    segments = []
    price_min = float(v.get("price_min") or 0)
    price_median = float(v.get("price_median") or max(price_min,1))
    vol = float(v.get("volatility") or 0)
    novelty = float(e.get("novelty_score") or 0)

    # Simple scoring anchors
    bargain = (price_min / max(price_median,1)) if price_median else 1.0
    bargain_score = max(-1.0, min(1.0, (1.0 - bargain) * 2.5))  # lower price → higher positive
    vol_score = max(-1.0, min(1.0, (vol / max(price_median,1)) * 2.0))
    nov_score = max(0.0, min(1.0, novelty / 10.0))

    # Build 8 segments
    t = 0.0
    for i in range(0, int(duration/seg_len)):
        base = bargain_score * (0.6 + 0.4*math.sin(i*0.6))
        jitter = (vol_score - 0.2) * (0.5 if i%2==0 else 0.3)
        s = max(-1.0, min(1.0, base + jitter))

        label = "positive" if s > 0.2 else ("negative" if s < -0.2 else "neutral")
        segments.append({"t0": round(t,2), "t1": round(t+seg_len,2), "label": label, "score": round(s,3)})
        t += seg_len

    # Summary
    pos = sum(1 for s in segments if s["label"]=="positive")
    neg = sum(1 for s in segments if s["label"]=="negative")
    neu = len(segments)-pos-neg

    return {
        "duration_sec": duration,
        "sound_pack": "Tropical Pop" if v.get("region")=="caribbean" else "8-Bit",
        "momentum_json": segments,
        "label_summary": {"positive_count": pos, "negative_count": neg, "neutral_count": neu},
    }

def run(days: int=7):
    settings.assert_minimum()
    sb = create_client(settings.supabase_url, settings.supabase_key)

    # Join flight_visibility and visibility_enrichment
    start = dt.date.today()
    end = start + dt.timedelta(days=days-1)
    vis = sb.table("flight_visibility").select("*").gte("date_bucket", str(start)).lte("date_bucket", str(end)).eq("region","caribbean").execute().data or []
    enr = sb.table("visibility_enrichment").select("*").gte("date_bucket", str(start)).lte("date_bucket", str(end)).eq("region","caribbean").execute().data or []

    # Index enrichment by key
    idx = {(e["origin"], e["destination"], e["date_bucket"]): e for e in enr}
    out_rows: List[dict] = []
    for v in vis:
        key = (v["origin"], v["destination"], v["date_bucket"])
        e = idx.get(key, {})
        moment = to_momentum_row(v, e)
        job_key = f"{v['origin']}-{v['destination']}-{v['date_bucket']}"
        out_rows.append({
            "region": v["region"],
            "theme": "caribbean_kokomo",
            "job_key": job_key,
            "momentum": moment["momentum_json"],
            "label_summary": moment["label_summary"],
            "duration_sec": moment["duration_sec"],
            "sound_pack": moment["sound_pack"]
        })

    # Upsert to momentum_bands
    for i in range(0, len(out_rows), 500):
        sb.table("momentum_bands").upsert(out_rows[i:i+500],
           on_conflict="region,theme,job_key").execute()
    print(f"🎶 momentum_bands upserted: {len(out_rows)}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args()
    run(days=args.days)
