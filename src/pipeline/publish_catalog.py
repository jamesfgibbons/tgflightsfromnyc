import json, datetime as dt
from typing import List
from supabase import create_client
from src.config import settings
from src.storage import write_json

def run(days: int=7):
    settings.assert_minimum()
    sb = create_client(settings.supabase_url, settings.supabase_key)

    start = dt.date.today()
    end = start + dt.timedelta(days=days-1)
    rows = (sb.table("momentum_bands")
              .select("region,theme,job_key,momentum,label_summary,duration_sec,sound_pack")
              .gte("created_at", str(start))
              .execute().data or [])

    catalog = {
        "generated": dt.datetime.utcnow().isoformat()+"Z",
        "vertical": "travel",
        "theme": "caribbean_kokomo",
        "items": []
    }
    for r in rows:
        job_id = r["job_key"]
        mp3_key = f"catalog/travel/flights_from_nyc/caribbean_kokomo/{job_id}.mp3"
        midi_key = f"catalog/travel/flights_from_nyc/caribbean_kokomo/{job_id}.mid"
        mp3_url = f"https://{settings.public_cdn_domain}/{mp3_key}" if settings.public_cdn_domain else mp3_key
        midi_url = f"https://{settings.public_cdn_domain}/{midi_key}" if settings.public_cdn_domain else midi_key
        catalog["items"].append({
            "job_id": job_id,
            "theme": r["theme"],
            "duration_sec": r["duration_sec"],
            "sound_pack": r["sound_pack"],
            "momentum_json": r["momentum"],
            "label_summary": r["label_summary"],
            "mp3_url": mp3_url,
            "midi_url": midi_url,
        })

    key = "catalog/travel/flights_from_nyc/caribbean_kokomo/catalog.json"
    write_json(settings.public_bucket, key, catalog, public=True, cache_control="public, max-age=86400")
    print(f"📤 Catalog written: {settings.public_bucket}/{key}")

if __name__ == "__main__":
    run()
