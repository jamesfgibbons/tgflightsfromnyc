"""
Deal Awareness API - "Where & When" Flow

Endpoints:
- GET /api/deals/evaluate - Evaluate deal quality for a route/month
- GET /api/deals/batch - Batch evaluate multiple routes

Uses Supabase RPC to call the evaluate_deal() PostgreSQL function.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
import os
import httpx
from datetime import datetime

router = APIRouter(prefix="/api/deals", tags=["deals"])

# Environment
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE = os.environ.get("SUPABASE_SERVICE_ROLE", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE:
    print("⚠️  WARNING: SUPABASE_URL or SUPABASE_SERVICE_ROLE not set. /api/deals/* will fail.")


# Response models
class Baseline(BaseModel):
    p25: float = Field(..., description="25th percentile price (30-day rolling)")
    p50: float = Field(..., description="50th percentile (median) price")
    p75: float = Field(..., description="75th percentile price")
    samples: int = Field(..., description="Number of price samples in baseline")
    last_updated: Optional[datetime] = Field(None, description="When baseline was last computed")


class SweetSpot(BaseModel):
    min_days: int = Field(..., description="Minimum lead time in sweet-spot window")
    max_days: int = Field(..., description="Maximum lead time in sweet-spot window")


class DealEvaluation(BaseModel):
    has_data: bool = Field(..., description="Whether sufficient data exists for evaluation")
    message: Optional[str] = Field(None, description="Error or warning message")
    origin: str
    dest: str
    month: int = Field(..., ge=1, le=12, description="Departure month (1-12)")
    cabin: str = Field(default="economy")
    depart_month: Optional[str] = Field(None, description="Actual departure month date (YYYY-MM-DD)")
    current_price: Optional[float] = Field(None, description="Current cheapest price for this route/month")
    baseline: Optional[Baseline] = Field(None, description="30-day rolling baseline")
    delta_pct: Optional[float] = Field(None, description="% difference from median baseline")
    deal_score: Optional[int] = Field(None, ge=0, le=100, description="Deal quality score (0-100)")
    sweet_spot: Optional[SweetSpot] = Field(None, description="Optimal booking window")
    recommendation: Optional[str] = Field(None, description="BUY, TRACK, or WAIT")
    confidence: Optional[int] = Field(None, ge=0, le=100, description="Recommendation confidence %")
    rationale: Optional[str] = Field(None, description="Human-readable explanation")
    last_seen: Optional[datetime] = Field(None, description="When current price was last observed")


class BatchEvaluateRequest(BaseModel):
    routes: List[dict] = Field(..., description="List of {origin, dest, month, cabin?} objects")


# Endpoints
@router.get("/evaluate", response_model=DealEvaluation)
async def evaluate_deal(
    origin: str = Query(..., min_length=3, max_length=3, description="Origin airport code (e.g., JFK)"),
    dest: str = Query(..., min_length=3, max_length=3, description="Destination airport code (e.g., MIA)"),
    month: int = Query(..., ge=1, le=12, description="Departure month (1-12)"),
    cabin: str = Query("economy", description="Cabin class (economy, premium, business, first)")
):
    """
    Evaluate deal quality for a specific route and month.

    Returns:
    - BUY: Excellent deal, book now
    - TRACK: Fair deal, monitor for improvements
    - WAIT: Poor deal, wait for prices to drop

    Includes:
    - Current price vs 30-day baseline (P25/P50/P75)
    - Deal score (0-100)
    - Sweet-spot booking window (if available)
    - Confidence level and rationale
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE:
        raise HTTPException(
            status_code=500,
            detail="Supabase not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE."
        )

    # Call Supabase RPC endpoint
    url = f"{SUPABASE_URL}/rest/v1/rpc/evaluate_deal"
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    payload = {
        "p_origin": origin.upper(),
        "p_dest": dest.upper(),
        "p_month": month,
        "p_cabin": cabin.lower()
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, headers=headers, json=payload)

        if response.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "Supabase RPC failed",
                    "status": response.status_code,
                    "message": response.text
                }
            )

        data = response.json()

        # Supabase RPC may return array or object depending on settings
        if isinstance(data, list) and len(data) > 0:
            data = data[0]

        return DealEvaluation(**data)

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Request to Supabase timed out")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Failed to connect to Supabase: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deal evaluation failed: {str(e)}")


@router.post("/batch", response_model=List[DealEvaluation])
async def batch_evaluate(request: BatchEvaluateRequest):
    """
    Batch evaluate multiple routes at once.

    Request body:
    {
      "routes": [
        {"origin": "JFK", "dest": "MIA", "month": 3},
        {"origin": "JFK", "dest": "LAX", "month": 6, "cabin": "business"}
      ]
    }

    Returns array of DealEvaluation objects.
    """
    results = []

    for route in request.routes:
        try:
            origin = route.get("origin", "")
            dest = route.get("dest", "")
            month = route.get("month", 1)
            cabin = route.get("cabin", "economy")

            eval_result = await evaluate_deal(origin, dest, month, cabin)
            results.append(eval_result)

        except HTTPException as e:
            # Include error as failed evaluation
            results.append(
                DealEvaluation(
                    has_data=False,
                    message=str(e.detail),
                    origin=route.get("origin", ""),
                    dest=route.get("dest", ""),
                    month=route.get("month", 1),
                    cabin=route.get("cabin", "economy")
                )
            )

    return results


@router.get("/health")
async def deals_health():
    """Check if deals API is operational."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE:
        return {
            "status": "unhealthy",
            "message": "Supabase credentials not configured"
        }

    return {
        "status": "healthy",
        "supabase_url": SUPABASE_URL.replace(SUPABASE_URL.split("//")[1].split(".")[0], "***"),
        "features": ["evaluate", "batch"]
    }
