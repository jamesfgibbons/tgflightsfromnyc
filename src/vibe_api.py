"""
Vibe Engine API: screenshot ingestion (OpenAI Vision + Spotify), motif upload, and
palette-driven generation that leverages the existing sonification service.
"""
from __future__ import annotations
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel, Field

from .storage import put_bytes, get_presigned_url
from .jobstore import job_store
from .api_models import JobResult, MomentumBand, LabelSummary
from .sonify_service import create_sonification_service
from .models import SonifyRequest
from .db import supabase_insert, supabase_select_one, supabase_select
import yaml
from .vibe_helpers import (
    extract_track_from_screenshot,
    fetch_spotify_audio_features,
    midi_events_to_midi_bytes,
    infer_music_features_llm,
    choose_palette_from_rules,
    normalize_features,
)

router = APIRouter(prefix="/api/vibe", tags=["vibe"])


def _artifact_bucket() -> str:
    return os.getenv("STORAGE_BUCKET", os.getenv("S3_BUCKET", "serpradio-artifacts"))


class GenerateRequest(BaseModel):
    dataset_ref: Optional[str] = None
    palette_slug: str = Field(default="caribbean_kokomo")
    sound_pack: Optional[str] = None
    use_wow: bool = True
    total_bars: int = 32
    tempo_hint: Optional[int] = None
    momentum_bands: Optional[List[Dict[str, Any]]] = None


@router.post("/screenshot", response_model=Dict[str, Any])
async def ingest_screenshot(
    file: Optional[UploadFile] = File(None),
    artist: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
):
    """Accept a screenshot (optional) or artist/title, infer features, map palette, store record."""
    key = None
    parsed = {"artist": artist, "track": title, "confidence": 0.0, "ocr_text": None}

    # If image provided, store and OCR
    if file is not None:
        data = await file.read()
        if not data:
            raise HTTPException(400, "Empty file")
        key = f"ingest/screenshots/{uuid.uuid4().hex}.png"
        put_bytes(_artifact_bucket(), key, data, "image/png")

        ocr = extract_track_from_screenshot(data)
        parsed.update(ocr)
        artist = (parsed.get("artist") or artist or "").strip()
        title = (parsed.get("track") or title or "").strip()

    if not (artist and title):
        raise HTTPException(422, "Supply a screenshot or artist/title form fields")

    # Feature extraction: Spotify optional
    use_spotify = os.getenv("VIBE_USE_SPOTIFY", "1") not in ("0", "false", "False")
    feats: Dict[str, Any] = {}
    if use_spotify:
        try:
            feats = fetch_spotify_audio_features(title, artist)
        except Exception:
            feats = {}
    if not feats:
        feats = infer_music_features_llm(artist, title)

    # Build normalized feature view and keep raw
    features_raw = dict(feats) if isinstance(feats, dict) else {}
    features_normalized = normalize_features(features_raw)

    # Rules-based palette mapping first
    palette_slug = choose_palette_from_rules(artist, title) or None

    # Fallback heuristic by features
    if not palette_slug:
        val = features_normalized["valence_0_1"]
        energy = features_normalized["energy_0_1"]
        if val >= 0.7 and 0.4 <= energy <= 0.75:
            palette_slug = "caribbean_kokomo"
        else:
            palette_slug = "synthwave_midnight" if energy < 0.55 else "arena_anthem"

    rec = {
        "image_url": key,
        "ocr_text": parsed.get("ocr_text"),
        "artist": artist,
        "track": title,
        "confidence": parsed.get("confidence", 0.0),
        "spotify_track_id": features_raw.get("track_id"),
        "audio_features": features_normalized,
        "palette_slug": palette_slug,
        "status": "verified",
        "created_at": datetime.utcnow().isoformat(),
    }
    supabase_insert("screenshot_ingests", rec)
    return {
        "ok": True,
        "record": rec,
        "features_raw": features_raw,
        "features_normalized": features_normalized,
    }


@router.get("/palettes", response_model=Dict[str, Any])
async def list_palettes(limit: int = 100):
    """List vibe palettes. Prefers Supabase table, falls back to config file."""
    rows = supabase_select("vibe_palettes", limit=limit)
    if rows:
        return {"items": rows, "source": "supabase"}
    # Fallback to config file
    cfg_path = os.getenv("VIBE_PALETTES_PATH", "config/vibe_palettes.yaml")
    try:
        with open(cfg_path, "r") as f:
            data = yaml.safe_load(f)
        return {"items": data or [], "source": "config"}
    except FileNotFoundError:
        return {"items": [], "source": "none"}


class MotifUpload(BaseModel):
    title: str
    bpm: int
    key_center: str
    bars: int
    events: List[Dict[str, Any]]  # [{t, on, note, vel, ch}]


@router.post("/motif", response_model=Dict[str, Any])
async def upload_motif(motif: MotifUpload):
    midi_bytes = midi_events_to_midi_bytes(motif.events, motif.bpm)
    key = f"motifs/{uuid.uuid4().hex}.mid"
    put_bytes(_artifact_bucket(), key, midi_bytes, "audio/midi")

    features = {
        "density": sum(1 for e in motif.events if e.get("on")),
    }
    rec = {
        "title": motif.title,
        "midi_url": key,
        "key_center": motif.key_center,
        "bpm": motif.bpm,
        "bars": motif.bars,
        "features": features,
    }
    supabase_insert("motifs", rec)
    return {"ok": True, "midi_key": key, "features": features}


@router.post("/generate", response_model=JobResult)
async def generate_with_palette(req: GenerateRequest):
    """Generate a track using a palette + optional momentum bands via existing service."""
    job_id = job_store.create()
    job_store.start(job_id)

    # Build momentum bands (fallback gentle-positive curve)
    bands: List[MomentumBand] = []
    if req.momentum_bands:
        for i, b in enumerate(req.momentum_bands):
            bands.append(
                MomentumBand(
                    t0=float(b.get("t0", i * 4.0)),
                    t1=float(b.get("t1", (i + 1) * 4.0)),
                    label=str(b.get("label", "neutral")),
                    score=float(b.get("score", 0.5)),
                )
            )
    else:
        bands = [
            MomentumBand(t0=0.0, t1=8.0, label="positive", score=0.62),
            MomentumBand(t0=8.0, t1=16.0, label="neutral", score=0.5),
            MomentumBand(t0=16.0, t1=32.0, label="positive", score=0.68),
        ]

    # Use existing service with override_metrics.momentum_data
    service = create_sonification_service(_artifact_bucket())
    spack = req.sound_pack or "Synthwave"
    tenant = "vibe_engine"
    output_base = f"{tenant}/vibe/{job_id}"
    sreq = SonifyRequest(
        tenant=tenant,
        source="demo",
        total_bars=req.total_bars,
        tempo_base=req.tempo_hint or 112,
        sound_pack=spack,
        override_metrics={"momentum_data": [b.model_dump() for b in bands]},
    )

    base = service.run_sonification(sreq, None, output_base)
    midi_key = base.get("midi_key")
    mp3_key = base.get("mp3_key")

    midi_url = get_presigned_url(_artifact_bucket(), midi_key) if midi_key else None
    mp3_url = get_presigned_url(_artifact_bucket(), mp3_key) if mp3_key else None

    # Simple label summary from bands
    ls = {"positive": 0, "neutral": 0, "negative": 0}
    for b in bands:
        if b.label in ls:
            ls[b.label] += 1

    res = JobResult(
        job_id=job_id,
        status="done",
        midi_url=midi_url,
        mp3_url=mp3_url,
        duration_sec=base.get("duration_sec", 32.0),
        sound_pack=spack,
        label_summary=LabelSummary(**ls),
        momentum_json=bands,
        logs=[f"palette={req.palette_slug}"],
    )

    # Persist job row (best-effort)
    supabase_insert(
        "sonification_jobs",
        {
            "job_id": job_id,
            "status": "done",
            "input_type": "palette",
            "dataset_ref": req.dataset_ref,
            "palette_slug": req.palette_slug,
            "sound_pack": spack,
            "midi_key": midi_key,
            "mp3_key": mp3_key,
            "momentum_json": [b.model_dump() for b in bands],
            "label_summary": ls,
            "duration_sec": res.duration_sec,
            "created_at": datetime.utcnow().isoformat(),
        },
    )

    job_store.finish(job_id, {"midi_url": midi_key, "mp3_url": mp3_key})
    return res
