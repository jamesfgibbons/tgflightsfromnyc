from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..supabase_db import get_client

router = APIRouter(prefix="/api/travel", tags=["travel"])


@router.get("/routes_nyc")
async def routes_nyc(origin: Optional[str] = Query(default=None), limit: int = Query(default=5000)):
    sb = get_client()
    try:
        q = sb.table("travel_routes_nyc").select("*")
        if origin:
            q = q.eq("origin", origin.upper())
        if limit and limit > 0:
            q = q.limit(limit)
        data = getattr(q.execute(), "data", []) or []
        return {"total": len(data), "items": data}
    except Exception as e:
        raise HTTPException(404, f"Routes unavailable: {e}")


@router.get("/price_quotes_latest")
async def price_quotes_latest(origin: Optional[str] = None, destination: Optional[str] = None, limit: int = 100):
    sb = get_client()
    try:
        # Try view first
        try:
            q = sb.table("vw_latest_price_quotes").select("*")
            if origin:
                q = q.eq("origin", origin.upper())
            if destination:
                q = q.eq("destination", destination.upper())
            if limit and limit > 0:
                q = q.limit(limit)
            data = getattr(q.execute(), "data", []) or []
            if data:
                return {"total": len(data), "items": data}
        except Exception:
            pass

        # Fallback to base table
        q = sb.table("price_quotes").select("*")
        if origin:
            q = q.eq("origin", origin.upper())
        if destination:
            q = q.eq("destination", destination.upper())
        if limit and limit > 0:
            q = q.limit(limit)
        data = getattr(q.execute(), "data", []) or []
        return {"total": len(data), "items": data}
    except Exception as e:
        raise HTTPException(404, f"Latest quotes unavailable: {e}")
