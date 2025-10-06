"""
Export catalog entries to Supabase tables (vibenet_runs, vibenet_items).
Best effort; no-op if Supabase env not set.
"""
from __future__ import annotations
import os
from datetime import datetime
from typing import List, Dict, Any

try:
    from supabase import create_client
except Exception:  # pragma: no cover
    create_client = None  # type: ignore


def _client():
    if not create_client:
        return None
    url = os.getenv("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )
    if not (url and key):
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


def export_catalog(entries: List[Any], *, channel: str, theme: str, sub_theme: str | None, catalog_key: str | None = None, notes: str | None = None) -> dict:
    sb = _client()
    if not sb:
        return {"ok": False, "reason": "supabase not configured"}

    try:
        # Create run row
        run = {
            "theme": theme,
            "sub_theme": sub_theme,
            "channel": channel,
            "generated": datetime.utcnow().isoformat(),
            "total": len(entries),
            "catalog_key": catalog_key,
            "notes": notes or "",
        }
        run_res = sb.table("vibenet_runs").insert(run).execute()
        run_id = run_res.data[0]["id"] if run_res.data else None
        if not run_id:
            return {"ok": False, "reason": "failed to create run"}

        rows = []
        for e in entries:
            rows.append(
                {
                    "run_id": run_id,
                    "entry_id": e.id,
                    "timestamp": e.timestamp,
                    "channel": e.channel,
                    "theme": getattr(e, "theme", None),
                    "sub_theme": getattr(e, "sub_theme", None),
                    "origin": getattr(e, "origin", None),
                    "destination": getattr(e, "destination", None),
                    "brand": e.brand,
                    "title": e.title,
                    "prompt": e.prompt,
                    "sound_pack": e.sound_pack,
                    "duration_sec": e.duration_sec,
                    "mp3_url": e.mp3_url,
                    "midi_url": e.midi_url,
                }
            )
        if rows:
            # batch insert in chunks
            for i in range(0, len(rows), 500):
                sb.table("vibenet_items").insert(rows[i : i + 500]).execute()

        return {"ok": True, "run_id": run_id, "inserted": len(rows)}
    except Exception as e:
        return {"ok": False, "reason": str(e)}
