"""
Web Search endpoints – Grok assisted websearch and summarization.

This provides a lightweight way to request a Grok-backed web search summary.
It crafts a strict-JSON prompt for xAI Grok and returns a normalized payload
with summary and citations. Works even when Webz.io is not configured.
"""
from __future__ import annotations
import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .llm_xai import call_xai_with_cache


router = APIRouter(prefix="/api/llm", tags=["llm"])


class GrokSearchRequest(BaseModel):
    q: str = Field(..., description="Query to search/summarize")
    max_citations: int = Field(default=5, ge=1, le=10)
    region: Optional[str] = Field(default=None, description="Optional region hint (e.g., US)")


class Citation(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    source: Optional[str] = None


class GrokSearchResponse(BaseModel):
    query: str
    summary: str
    citations: list[Citation] = Field(default_factory=list)
    raw: Optional[Dict[str, Any]] = None


def _build_grok_prompt(q: str, n: int, region: Optional[str]) -> str:
    return (
        "Research the following query using up-to-date web sources and return a concise, factual summary.\n"
        f"Query: {q}\n"
        + (f"Region: {region}\n" if region else "")
        + "Return STRICT JSON with keys: query, summary (<= 120 words), citations (array of {title,url,source domain})."
    )


@router.get("/grok_search", response_model=GrokSearchResponse)
async def grok_search(q: str = Query(...), max_citations: int = Query(5, ge=1, le=10), region: Optional[str] = Query(None)):
    prompt = _build_grok_prompt(q, max_citations, region)
    system = (
        "You are Grok with web access. Perform web search and include recent sources."
        " Output STRICT JSON only: {\"query\":str,\"summary\":str,\"citations\":[{\"title\":str,\"url\":str,\"source\":str}]}."
        f" Limit citations to {max_citations}."
    )
    res = call_xai_with_cache(prompt, system=system, metadata={"kind": "grok_search", "query": q})
    raw = res.get("response_raw") or {}

    # Try to extract model content JSON
    content: Optional[str] = None
    try:
        # xAI returns OpenAI-compatible schema
        choices = (raw.get("choices") or [])
        if choices:
            msg = (choices[0] or {}).get("message") or {}
            content = msg.get("content")
    except Exception:
        content = None

    parsed: Dict[str, Any]
    if content:
        try:
            parsed = json.loads(content)
        except Exception:
            # Best-effort fallback: wrap content as summary only
            parsed = {"query": q, "summary": content, "citations": []}
    else:
        # No content; return error payload
        raise HTTPException(502, f"Grok response unavailable: {raw}")

    # Trim citations to requested count
    cites = parsed.get("citations") or []
    if isinstance(cites, list) and len(cites) > max_citations:
        parsed["citations"] = cites[:max_citations]

    return GrokSearchResponse(query=parsed.get("query") or q, summary=parsed.get("summary") or "", citations=parsed.get("citations") or [], raw=raw)

