"""
Notifications API: exposes board badges and route events derived from the
notification_events table and the board_badges_live materialized view.

Contracts are optimized for the Split‑Flap UI overlays.
"""
from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Query

from .db import supabase_select


router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("/board")
def board_badges(origins: Optional[str] = Query(None)):
    rows = supabase_select("board_badges_live", limit=1000) or []
    if origins:
        allow = {o.strip().upper() for o in origins.split(",") if o.strip()}
        rows = [r for r in rows if (r.get("origin") or "").upper() in allow]

    items = []
    for r in rows:
        drop_pct = r.get("drop_pct")
        labels = []
        if drop_pct is not None:
            try:
                pct = abs(float(drop_pct))
                labels.append(f"{pct:.0f}% drop")
            except Exception:
                pass
        if r.get("window_open"):
            labels.append("window open")

        items.append({
            "id": f"{r.get('origin')}-{r.get('dest')}",
            "origin": r.get("origin"),
            "dest": r.get("dest"),
            "labels": labels,
            "severity": r.get("top_severity", "info"),
            "lastSeen": r.get("last_seen"),
        })

    return {"items": items}


@router.get("/route")
def route_events(origin: str, dest: str, hours: int = 168):
    # Basic query; for Supabase we filter in the client
    rows = supabase_select("notification_events", limit=2000) or []
    origin_u, dest_u = origin.upper(), dest.upper()
    out = []
    for r in rows:
        if (r.get("origin") or "").upper() == origin_u and (r.get("dest") or "").upper() == dest_u:
            out.append(r)
    return {"events": out}

