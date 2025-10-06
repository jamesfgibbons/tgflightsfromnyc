"""
Batch sonification: uses existing service to render MP3/MIDI and writes a public catalog.
"""
import os, json, time
from typing import List, Dict, Any
from datetime import datetime
from ..sonify_service import create_sonification_service
from .exporters.supabase_export import export_catalog
from ..models import SonifyRequest
from ..storage import get_presigned_url, write_json, put_bytes
from .schemas import CacheEntry

# Support both S3 and Supabase
STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", os.getenv("S3_BUCKET", "serpradio-artifacts"))
PUBLIC_BUCKET = os.getenv("PUBLIC_STORAGE_BUCKET", os.getenv("S3_PUBLIC_BUCKET", "serpradio-public"))

def render_batch(plans: List[Dict[str,Any]]) -> List[CacheEntry]:
    service = create_sonification_service(STORAGE_BUCKET)
    results: List[CacheEntry] = []

    for item in plans:
        plan = item["plan"]
        segs = plan["momentum"]
        # Map momentum to override metrics (minimal – service will also use momentum bands if supported)
        override = {"momentum_data": segs}

        req = SonifyRequest(
            tenant="pipeline_travel",
            source="demo",
            sound_pack=plan["sound_pack"],
            total_bars=plan["total_bars"],
            tempo_base=plan["tempo_base"],
            override_metrics=override
        )
        # Create deterministic output base for catalog assets
        output_base = f"catalog/{item['channel']}/{item.get('theme','')}/{item.get('sub_theme','')}/{item['id']}".strip('/')
        output_base = f"{req.tenant}/{output_base}" if not output_base.startswith(req.tenant) else output_base
        base = service.run_sonification(req, None, output_base)  # returns midi_key/mp3_key/momentum_data/label_summary

        # Prepare public URLs (streamable)
        midi_url = get_presigned_url(STORAGE_BUCKET, base.get("midi_key")) if base.get("midi_key") else None
        mp3_url  = get_presigned_url(STORAGE_BUCKET, base.get("mp3_key"))  if base.get("mp3_key")  else None

        # Duration fallback
        duration = base.get("duration_sec") or 32.0

        entry = CacheEntry(
            id=item["id"],
            timestamp=item["timestamp"],
            channel=item["channel"],
            theme=item.get("theme"),
            sub_theme=item.get("sub_theme"),
            brand=item.get("brand"),
            title=item["title"],
            prompt=item["prompt"],
            origin=item.get("origin"),
            destination=item.get("destination"),
            sound_pack=plan["sound_pack"],
            duration_sec=duration,
            mp3_url=mp3_url,
            midi_url=midi_url,
            momentum_json=base.get("momentum_data") or segs,
            label_summary=base.get("label_summary") or plan["label_summary"]
        )
        results.append(entry)

    return results

def publish_catalog(entries: List[CacheEntry], catalog_prefix: str = "catalog/travel"):
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    latest_key = f"{catalog_prefix}/latest.json"
    dated_key  = f"{catalog_prefix}/{date_str}.json"

    payload = {
        "generated": datetime.utcnow().isoformat(),
        "total": len(entries),
        "items": [e.model_dump() for e in entries]
    }
    # store to PUBLIC bucket for easy frontend consumption
    write_json(PUBLIC_BUCKET, latest_key, payload, public=True, cache_control="public, max-age=1800")
    write_json(PUBLIC_BUCKET, dated_key,  payload, public=True, cache_control="public, max-age=31536000")

    # optional: export to Supabase tables if configured
    try:
        channel = entries[0].channel if entries else "travel"
        theme = getattr(entries[0], "theme", None) or catalog_prefix.split("/")[-1]
        sub_theme = getattr(entries[0], "sub_theme", None)
        export_catalog(entries, channel=channel, theme=theme, sub_theme=sub_theme, catalog_key=latest_key,
                       notes=f"published {len(entries)} entries to {latest_key}")
    except Exception:
        pass
