from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .storage import get_supabase_client, get_storage_backend


router = APIRouter(prefix="/api/book", tags=["best-time"])


class LeadPoint(BaseModel):
    lead: int
    q10: Optional[float] = None
    q25: Optional[float] = None
    q50: Optional[float] = None
    q75: Optional[float] = None
    n: int
    volatility: Optional[float] = None
    dropProb: Optional[float] = None


class LeadCurve(BaseModel):
    origin: str
    dest: str
    month: int
    cabin: str = "economy"
    points: List[LeadPoint]


class BestTimeSummary(BaseModel):
    origin: str
    dest: str
    month: int
    cabin: str
    bwi: int
    sweetSpot: List[int]
    todayPrice: Optional[float]
    deltaPct: Optional[float]
    rec: str
    confidence: int
    rationale: str


@router.get("/lead_time_curve", response_model=LeadCurve)
def lead_time_curve(origin: str, dest: str, month: int, cabin: str = "economy"):
    if get_storage_backend() != "supabase":
        raise HTTPException(503, "database not configured")
    sb = get_supabase_client()
    try:
        res = sb.rpc(
            "lead_time_curve_fn",
            {"p_origin": origin.upper(), "p_dest": dest.upper(), "p_month": int(month), "p_cabin": cabin},
        ).execute()
        rows = getattr(res, "data", []) or []
    except Exception as e:
        raise HTTPException(500, f"curve query failed: {e}")
    pts: List[LeadPoint] = []
    for r in rows:
        pts.append(
            LeadPoint(
                lead=int(r.get("lead", 0)),
                q10=_f(r.get("q10")),
                q25=_f(r.get("q25")),
                q50=_f(r.get("q50")),
                q75=_f(r.get("q75")),
                n=int(r.get("n", 0)),
                volatility=_f(r.get("volatility")),
                dropProb=_f(r.get("drop_prob")),
            )
        )
    return LeadCurve(origin=origin.upper(), dest=dest.upper(), month=int(month), cabin=cabin, points=pts)


@router.get("/summary", response_model=BestTimeSummary)
def best_time_summary(origin: str, dest: str, month: int, cabin: str = "economy"):
    if get_storage_backend() != "supabase":
        raise HTTPException(503, "database not configured")
    sb = get_supabase_client()
    try:
        res = sb.rpc(
            "best_time_summary_fn",
            {"p_origin": origin.upper(), "p_dest": dest.upper(), "p_month": int(month), "p_cabin": cabin},
        ).execute()
        row = (getattr(res, "data", []) or [None])[0]
    except Exception as e:
        raise HTTPException(500, f"summary query failed: {e}")
    if not row:
        return BestTimeSummary(
            origin=origin.upper(),
            dest=dest.upper(),
            month=int(month),
            cabin=cabin,
            bwi=50,
            sweetSpot=[45, 75],
            todayPrice=None,
            deltaPct=None,
            rec="TRACK",
            confidence=50,
            rationale="Insufficient data; tracking recommended.",
        )
    return BestTimeSummary(
        origin=str(row.get("origin", origin.upper())),
        dest=str(row.get("destination", dest.upper())),
        month=int(row.get("month", int(month))),
        cabin=str(row.get("cabin", cabin)),
        bwi=int(row.get("bwi", 50)),
        sweetSpot=[int(row.get("sweet_spot_start", 45)), int(row.get("sweet_spot_end", 75))],
        todayPrice=_f(row.get("today_price")),
        deltaPct=_f(row.get("delta_pct")),
        rec=str(row.get("rec", "TRACK")),
        confidence=int(row.get("confidence", 70)),
        rationale=str(row.get("rationale", "Based on historical medians.")),
    )


def _f(x) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None

