from __future__ import annotations
import json
import math
import os
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/board", tags=["board"])


def _dataset_path() -> str:
    return os.getenv("BOARD_DATASET_PATH", "data/grok_dataset_sample.json")


def _safe_load_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(404, f"dataset not found: {path}")
    except json.JSONDecodeError as e:
        raise HTTPException(500, f"dataset parse error: {e}")


_CACHE: Dict[str, Dict[str, Any]] = {}
_EXP: Dict[str, float] = {}


def _ttl_sec() -> int:
    try:
        return max(1, int(os.getenv("BOARD_FEED_TTL_SEC", "45")))
    except Exception:
        return 45


def _normalize(vals: List[float]) -> List[float]:
    if not vals:
        return []
    vmin, vmax = min(vals), max(vals)
    if vmax == vmin:
        return [0.5] * len(vals)
    return [(v - vmin) / (vmax - vmin) for v in vals]


class BoardRow(BaseModel):
    id: str
    title: str
    data_window: Optional[str] = None
    vibe: Dict[str, float]
    tempo_bpm: int
    momentum: Dict[str, int]
    palette: str = "default"
    last_updated: Optional[str] = None
    spark: List[float] = Field(default_factory=list)


class BoardFeedResponse(BaseModel):
    items: List[BoardRow]
    source: str


@router.get("/feed", response_model=BoardFeedResponse)
async def board_feed(
    target: str = Query(default="keywords"),
    limit: int = Query(default=12, ge=1, le=50),
    lookback_days: int = Query(default=30, ge=7, le=365),
):
    path = _dataset_path()
    try:
        mtime = os.path.getmtime(path)
    except FileNotFoundError:
        raise HTTPException(404, f"dataset not found: {path}")

    key = f"{path}|{target}|{limit}|{lookback_days}|{int(mtime)}"
    now = time.time()
    if key in _CACHE and now < _EXP.get(key, 0.0):
        return _CACHE[key]

    data = _safe_load_json(path)
    series = data.get("time_series") or []
    window = series[-lookback_days:] if len(series) > lookback_days else series
    vals: List[float] = []
    for r in window:
        try:
            vals.append(float(r.get("organic_traffic")))
        except Exception:
            continue
    norm = _normalize(vals) or [0.4, 0.5, 0.6, 0.55, 0.5]

    # Very simple vibe & tempo from sparkline
    avg = sum(norm) / len(norm)
    diffs = [abs(a - b) for a, b in zip(norm[1:], norm[:-1])]
    energy = (sum(diffs) / max(1, len(diffs))) if diffs else 0.2
    tempo = int(104 + min(1.0, energy * 2.0) * (120 - 104))
    momentum = {"positive": 0, "neutral": len(norm), "negative": 0}

    items: List[BoardRow] = []
    source_list = data.get("keywords_top") if target == "keywords" else data.get("entities_top")
    if not isinstance(source_list, list):
        source_list = []
    for entry in source_list[:limit]:
        title = str(entry.get("keyword") or entry.get("name") or "?")
        if not title:
            continue
        items.append(BoardRow(
            id=title.lower().replace(" ", "-")[:48],
            title=title,
            data_window=(window[0].get("date") + ".." + window[-1].get("date")) if window else None,
            vibe={"valence": avg, "arousal": energy, "tension": max(0.0, 0.8 - avg)},
            tempo_bpm=tempo,
            momentum=momentum,
            last_updated=window[-1].get("date") if window else None,
            spark=norm,
        ))

    if not items:
        items = [BoardRow(
            id="overall",
            title=str(data.get("source") or "site-wide"),
            data_window=(window[0].get("date") + ".." + window[-1].get("date")) if window else None,
            vibe={"valence": avg, "arousal": energy, "tension": max(0.0, 0.8 - avg)},
            tempo_bpm=tempo,
            momentum=momentum,
            last_updated=window[-1].get("date") if window else None,
            spark=norm,
        )]

    resp = BoardFeedResponse(items=items, source=os.path.basename(path))
    payload = json.loads(resp.model_dump_json())
    _CACHE[key] = payload
    _EXP[key] = now + _ttl_sec()
    return payload

