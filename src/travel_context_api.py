"""
Travel Context API: summarize latest route-specific context for overlays.

Primary source:
- data/grok_websearch_routes.json (artifact from scripts/run_grok_websearch_routes.py)

Fallbacks:
- Supabase 'llm_results' (when available) with simple heuristics by prompt containing
  both origin and destination strings.

Endpoint:
- GET /api/travel/context?origin=JFK&destination=MIA
  Returns: { origin, destination, status, summary, citations, source }

Notes:
- Designed to be resilient even when upstream keys are missing. If we have no
  usable content, returns status:"unavailable" with a friendly message.
"""
from __future__ import annotations
import json
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .db import supabase_select


router = APIRouter(prefix="/api/travel", tags=["travel"])


class ContextCitation(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None


class TravelContextResponse(BaseModel):
    origin: str
    destination: str
    status: str = Field(description="ok | unavailable | error")
    summary: Optional[str] = None
    citations: List[ContextCitation] = Field(default_factory=list)
    source: Optional[str] = Field(default=None, description="where the context came from")


def _artifact_path() -> str:
    return os.getenv("TRAVEL_CONTEXT_DATASET", "data/grok_websearch_routes.json")


def _load_artifact(path: str) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def _match_item(items: List[Dict[str, Any]], origin: str, destination: str) -> Optional[Dict[str, Any]]:
    o = origin.upper().strip()
    d = destination.upper().strip()
    for it in items:
        if (it.get("origin") or "").upper() == o and (it.get("destination") or "").upper() == d:
            return it
    return None


@router.get("/context", response_model=TravelContextResponse)
async def travel_context(
    origin: str = Query(..., min_length=2, max_length=6),
    destination: str = Query(..., min_length=2, max_length=6),
):
    # 1) Try local artifact
    art = _load_artifact(_artifact_path())
    if art and isinstance(art.get("items"), list):
        m = _match_item(art["items"], origin, destination)
        if m:
            # Expect Grok JSON content in result.response_raw. The demo artifact may contain errors; handle gracefully.
            raw = (m.get("result") or {}).get("response_raw") or {}
            # Attempt to parse model JSON content field (OpenAI-compatible) if present
            content_summary: Optional[str] = None
            citations: List[ContextCitation] = []
            try:
                # If raw has choices/message/content JSON, parse it
                choices = raw.get("choices") or []
                if choices:
                    msg = (choices[0] or {}).get("message") or {}
                    content = msg.get("content")
                    if content and isinstance(content, str):
                        data = json.loads(content)
                        content_summary = data.get("summary") or content
                        for c in data.get("citations") or []:
                            citations.append(ContextCitation(**{k: c.get(k) for k in ("title", "url", "source")}))
            except Exception:
                # Not JSON content; try human-readable fallback if present
                if isinstance(raw, dict):
                    content_summary = raw.get("summary") or content_summary

            if content_summary:
                return TravelContextResponse(
                    origin=origin,
                    destination=destination,
                    status="ok",
                    summary=content_summary,
                    citations=citations,
                    source=os.path.basename(_artifact_path()),
                )
            # Artifact exists but lacks usable content
            return TravelContextResponse(
                origin=origin,
                destination=destination,
                status="unavailable",
                summary=(
                    "Context artifact found for this route, but no usable summary was available. "
                    "Re-run Grok websearch with a valid API key to populate summaries."
                ),
                citations=[],
                source=os.path.basename(_artifact_path()),
            )

    # 2) Fallback: Supabase llm_results (heuristic by prompt text)
    try:
        rows = supabase_select("llm_results", limit=500) or []
        needle_o, needle_d = origin.upper(), destination.upper()
        for r in rows:
            prompt = (r.get("prompt") or "").upper()
            if needle_o in prompt and needle_d in prompt:
                raw = r.get("response_raw") or {}
                summary = None
                citations: List[ContextCitation] = []
                try:
                    choices = raw.get("choices") or []
                    if choices:
                        msg = (choices[0] or {}).get("message") or {}
                        content = msg.get("content")
                        if content and isinstance(content, str):
                            data = json.loads(content)
                            summary = data.get("summary") or content
                            for c in data.get("citations") or []:
                                citations.append(ContextCitation(**{k: c.get(k) for k in ("title", "url", "source")}))
                except Exception:
                    if isinstance(raw, dict):
                        summary = raw.get("summary") or summary

                if summary:
                    return TravelContextResponse(
                        origin=origin,
                        destination=destination,
                        status="ok",
                        summary=summary,
                        citations=citations,
                        source="supabase.llm_results",
                    )
    except Exception:
        # Supabase not configured or error – continue to final fallback
        pass

    # 3) Nothing available
    return TravelContextResponse(
        origin=origin,
        destination=destination,
        status="unavailable",
        summary=(
            "No context available yet. Trigger Grok websearch for this route or seed from Supabase."
        ),
        citations=[],
        source=None,
    )

