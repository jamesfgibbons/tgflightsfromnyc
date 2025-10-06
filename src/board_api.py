"""
Split-Flap Board API: serves precomputed slice rows for the split-flap UI.

Reads a Grok-ready dataset (see scripts/build_grok_viz_dataset.py) and returns
rows with vibe chips, tempo, momentum label counts, and a compact sparkline to
animate the board. Keeps the front-end lightweight and cost-controlled.
"""
from __future__ import annotations
import os
import json
import math
from typing import Any, Dict, List, Optional, Literal
import time

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .vibe_encoder import embed_vibe
from .vibenet_api import _normalize as _vn_normalize, _segments_to_bands as _vn_segments_to_bands


router = APIRouter(prefix="/api/board", tags=["board"])


def _dataset_path(default: Optional[str] = None) -> str:
    return os.getenv("BOARD_DATASET_PATH", default or "data/grok_tips_inspiration_dataset.json")


def _safe_load_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(404, f"dataset not found: {path}")
    except json.JSONDecodeError as e:
        raise HTTPException(500, f"dataset parse error: {e}")


# In-process cache for feed responses (avoids disk I/O between polls)
_FEED_CACHE: Dict[str, Dict[str, Any]] = {}
_FEED_EXP: Dict[str, float] = {}


def _ttl_sec() -> int:
    try:
        return max(1, int(os.getenv("BOARD_FEED_TTL_SEC", "45")))
    except Exception:
        return 45


def _cache_key(target: str, limit: int, lookback_days: int, palette_slug: Optional[str], path: str, mtime: float) -> str:
    return f"{target}|{limit}|{lookback_days}|{palette_slug or ''}|{path}|{int(mtime)}"


def _tail_series(series: List[Dict[str, Any]], key: str, days: int) -> List[float]:
    tail = series[-days:] if days > 0 and len(series) > days else series
    vals: List[float] = []
    for r in tail:
        try:
            v = float(r.get(key))
        except Exception:
            v = math.nan
        if not math.isnan(v):
            vals.append(v)
    return vals


def _tempo_from_series(norm: List[float], tempo_min: int = 104, tempo_max: int = 120) -> int:
    diffs = [abs(a - b) for a, b in zip(norm[1:], norm[:-1])]
    energy = sum(diffs) / max(1, len(diffs)) if diffs else 0.2
    return int(tempo_min + min(1.0, energy * 2.0) * (tempo_max - tempo_min))


class BoardRow(BaseModel):
    id: str
    title: str
    data_window: Optional[str] = None
    vibe: Dict[str, Any]
    tempo_bpm: int
    momentum: Dict[str, int]
    palette: str
    last_updated: Optional[str] = None
    spark: List[float] = Field(default_factory=list, description="Normalized sparkline (0..1)")


class BoardFeedResponse(BaseModel):
    items: List[BoardRow]
    source: str


@router.get("/feed", response_model=BoardFeedResponse)
async def board_feed(
    target: Literal["keywords", "entities", "overall"] = Query(default="keywords"),
    limit: int = Query(default=12, ge=1, le=50),
    lookback_days: int = Query(default=30, ge=7, le=365),
    palette_slug: Optional[str] = Query(default=None),
    dataset: Optional[str] = Query(default=None, description="Override dataset path"),
):
    """Provide board rows using the Grok dataset. Keeps engine and UI decoupled.

    - target=keywords → titles from keywords_top
    - target=entities → titles from entities_top
    - target=overall  → single site-wide row
    """
    path = dataset or _dataset_path()
    try:
        mtime = os.path.getmtime(path)
    except FileNotFoundError:
        raise HTTPException(404, f"dataset not found: {path}")

    key = _cache_key(target, limit, lookback_days, palette_slug, path, mtime)
    now = time.time()
    if key in _FEED_CACHE and now < _FEED_EXP.get(key, 0.0):
        return _FEED_CACHE[key]

    data = _safe_load_json(path)

    series = data.get("time_series") or []
    # Use organic_traffic for board spark/vibe (fallback if missing)
    vals = _tail_series(series, "organic_traffic", lookback_days) if series else []
    if len(vals) < 4:
        # Fallback: synthesize from keywords/entities weights
        weights: List[float] = []
        if target == "keywords":
            for k in (data.get("keywords_top") or [])[:max(8, limit)]:
                try:
                    weights.append(float(k.get("organic_traffic") or 0.0))
                except Exception:
                    continue
        elif target == "entities":
            for e in (data.get("entities_top") or [])[:max(8, limit)]:
                try:
                    weights.append(float(e.get("traffic") or 0.0))
                except Exception:
                    continue
        if not weights:
            # final minimal fallback
            vals = [0.4, 0.5, 0.45, 0.5, 0.55]
        else:
            # normalize weights to sparkline length 8
            while len(weights) < 8:
                weights = weights + weights
            weights = weights[:8]
            vmin, vmax = min(weights), max(weights)
            vals = [
                0.5 if vmax == vmin else (w - vmin) / (vmax - vmin)
                for w in weights
            ]

    # Build vibe/tempo/momentum from the same series for consistency
    vibe_vec = embed_vibe(vals, palette_slug)
    norm = _vn_normalize(vals)
    bands = _vn_segments_to_bands(norm, min(10, max(3, len(norm) // 8)))
    tempo = _tempo_from_series(norm)
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for b in bands:
        if b.label in counts:
            counts[b.label] += 1

    # Determine row titles based on target
    items: List[BoardRow] = []
    if target == "keywords":
        kws = (data.get("keywords_top") or [])[:limit]
        for k in kws:
            title = str(k.get("keyword"))
            if not title:
                continue
            items.append(
                BoardRow(
                    id=_slug(title),
                    title=title,
                    data_window=_data_window(series, lookback_days),
                    vibe={
                        "valence": vibe_vec.valence,
                        "arousal": vibe_vec.arousal,
                        "tension": vibe_vec.tension,
                    },
                    tempo_bpm=tempo,
                    momentum=counts,
                    palette=vibe_vec.palette,
                    last_updated=_latest_date(series),
                    spark=norm,
                )
            )
    elif target == "entities":
        ents = (data.get("entities_top") or [])[:limit]
        for e in ents:
            title = str(e.get("name"))
            if not title:
                continue
            items.append(
                BoardRow(
                    id=_slug(title),
                    title=title,
                    data_window=_data_window(series, lookback_days),
                    vibe={
                        "valence": vibe_vec.valence,
                        "arousal": vibe_vec.arousal,
                        "tension": vibe_vec.tension,
                    },
                    tempo_bpm=tempo,
                    momentum=counts,
                    palette=vibe_vec.palette,
                    last_updated=_latest_date(series),
                    spark=norm,
                )
            )
    else:  # overall
        items.append(
            BoardRow(
                id="overall",
                title=str(data.get("source") or "site-wide"),
                data_window=_data_window(series, lookback_days),
                vibe={
                    "valence": vibe_vec.valence,
                    "arousal": vibe_vec.arousal,
                    "tension": vibe_vec.tension,
                },
                tempo_bpm=tempo,
                momentum=counts,
                palette=vibe_vec.palette,
                last_updated=_latest_date(series),
                spark=norm,
            )
        )

    resp = BoardFeedResponse(items=items, source=os.path.basename(path))
    payload = json.loads(resp.model_dump_json())
    _FEED_CACHE[key] = payload
    _FEED_EXP[key] = now + _ttl_sec()
    return payload


def _slug(s: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in s).strip("-")[:64]


def _data_window(series: List[Dict[str, Any]], days: int) -> Optional[str]:
    if not series:
        return None
    tail = series[-days:] if len(series) > days else series
    try:
        start = tail[0]["date"][:10]
        end = tail[-1]["date"][:10]
        return f"{start}..{end}"
    except Exception:
        return None


def _latest_date(series: List[Dict[str, Any]]) -> Optional[str]:
    try:
        return series[-1]["date"][:10]
    except Exception:
        return None
