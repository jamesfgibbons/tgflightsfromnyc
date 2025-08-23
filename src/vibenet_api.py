"""
VibeNet API: generic data → vibe sonification aligned with SERPRadio.
"""
from __future__ import annotations
import os
import math
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .db import supabase_select
from .storage import get_presigned_url
from .jobstore import job_store
from .sonify_service import create_sonification_service
from .models import SonifyRequest
from .api_models import JobResult, MomentumBand, LabelSummary

import yaml


router = APIRouter(prefix="/vibenet", tags=["vibenet"])


def _load_palettes() -> List[Dict[str, Any]]:
    # prefer Supabase if configured
    rows = supabase_select("vibe_palettes", limit=100)
    if rows:
        return rows
    # fallback to config file
    path = os.getenv("VIBE_PALETTES_PATH", "config/vibe_palettes.yaml")
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f) or []
    except FileNotFoundError:
        return []


def _palette_to_sound_pack(slug: str, palettes: List[Dict[str, Any]]) -> str:
    # default mapping if not found
    default = {
        "caribbean_kokomo": "Tropical Pop",
        "synthwave_midnight": "Synthwave",
        "arena_anthem": "Arena Rock",
    }.get(slug)
    for p in palettes:
        if str(p.get("slug")) == slug:
            dp = p.get("default_pack") or default
            return dp or "Synthwave"
    return default or "Synthwave"


class VibesResponse(BaseModel):
    items: List[Dict[str, Any]]
    source: str


@router.get("/vibes", response_model=VibesResponse)
async def list_vibes():
    rows = supabase_select("vibe_palettes", limit=100)
    if rows:
        return VibesResponse(items=rows, source="supabase")
    path = os.getenv("VIBE_PALETTES_PATH", "config/vibe_palettes.yaml")
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f) or []
        return VibesResponse(items=data, source="config")
    except FileNotFoundError:
        return VibesResponse(items=[], source="none")


class GenerateControls(BaseModel):
    bars: int = Field(default=16, ge=4, le=128)
    tempo_hint: Optional[int] = Field(default=None, ge=60, le=180)


class VibeNetGenerateRequest(BaseModel):
    data: List[float] = Field(default_factory=list, description="Primary numeric series")
    vibe_slug: str = Field(default="synthwave_midnight")
    controls: GenerateControls = Field(default_factory=GenerateControls)


def _normalize(vals: List[float]) -> List[float]:
    if not vals:
        return []
    vmin = min(vals)
    vmax = max(vals)
    if math.isclose(vmax, vmin):
        return [0.5 for _ in vals]
    return [(v - vmin) / (vmax - vmin) for v in vals]


def _segments_to_bands(norm: List[float], segment_count: int) -> List[MomentumBand]:
    if segment_count <= 0:
        segment_count = 8
    n = len(norm)
    if n == 0:
        # default gentle positive
        return [
            MomentumBand(t0=0.0, t1=6.4, label="positive", score=0.6),
            MomentumBand(t0=6.4, t1=12.8, label="neutral", score=0.5),
        ]
    size = max(1, n // segment_count)
    bands: List[MomentumBand] = []
    t = 0.0
    for i in range(segment_count):
        start = i * size
        end = n if i == segment_count - 1 else min(n, (i + 1) * size)
        if start >= end:
            mean = sum(norm) / len(norm)
        else:
            mean = sum(norm[start:end]) / (end - start)
        score = max(-1.0, min(1.0, (mean - 0.5) * 2.0))
        label = "positive" if score > 0.15 else ("negative" if score < -0.15 else "neutral")
        bands.append(MomentumBand(t0=t, t1=t + 3.2, label=label, score=round(score, 3)))
        t += 3.2
    return bands


@router.post("/generate", response_model=JobResult)
async def generate(req: VibeNetGenerateRequest):
    if not isinstance(req.data, list) or len(req.data) < 4:
        raise HTTPException(400, "data must be a numeric array with at least 4 points")

    palettes = _load_palettes()
    sound_pack = _palette_to_sound_pack(req.vibe_slug, palettes)

    # Map data → momentum bands as a simple, musical proxy
    norm = _normalize([float(x) for x in req.data])
    segment_count = min(10, max(3, len(norm) // 8))
    bands = _segments_to_bands(norm, segment_count)

    # Tempo heuristic: use controls or palette tempo range, scale by volatility
    tempo = req.controls.tempo_hint
    if tempo is None:
        # palette tempo range if available
        tempo_min, tempo_max = 104, 120
        for p in palettes:
            if str(p.get("slug")) == req.vibe_slug:
                tempo_min = int(p.get("tempo_min", tempo_min))
                tempo_max = int(p.get("tempo_max", tempo_max))
                break
        diffs = [abs(a - b) for a, b in zip(norm[1:], norm[:-1])]
        energy = sum(diffs) / max(1, len(diffs)) if diffs else 0.2
        tempo = int(tempo_min + min(1.0, energy * 2.0) * (tempo_max - tempo_min))

    # Prepare sonification via existing service
    service = create_sonification_service(os.getenv("STORAGE_BUCKET", os.getenv("S3_BUCKET", "serpradio-artifacts")))
    tenant = "vibenet"
    job_id = job_store.create()
    job_store.start(job_id)
    output_base = f"{tenant}/jobs/{job_id}"

    sreq = SonifyRequest(
        tenant=tenant,
        source="demo",
        total_bars=req.controls.bars,
        tempo_base=tempo,
        sound_pack=sound_pack,
        override_metrics={"momentum_data": [b.model_dump() for b in bands]},
    )

    base = service.run_sonification(sreq, None, output_base)

    midi_key = base.get("midi_key")
    mp3_key = base.get("mp3_key")
    midi_url = get_presigned_url(service.s3_bucket, midi_key) if midi_key else None
    mp3_url = get_presigned_url(service.s3_bucket, mp3_key) if mp3_key else None

    # Label summary
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for b in bands:
        if b.label in counts:
            counts[b.label] += 1

    res = JobResult(
        job_id=job_id,
        status="done",
        midi_url=midi_url,
        mp3_url=mp3_url,
        duration_sec=base.get("duration_sec", float(req.controls.bars) * 60.0 / tempo),
        sound_pack=sound_pack,
        label_summary=LabelSummary(**counts),
        momentum_json=bands,
        logs=[f"vibe={req.vibe_slug}", f"sound_pack={sound_pack}", f"tempo={tempo}"],
    )

    job_store.finish(job_id, {"midi_url": midi_key, "mp3_url": mp3_key})
    return res

