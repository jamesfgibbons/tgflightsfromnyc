from __future__ import annotations
import os
import json
import time
import requests
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.get("/grok_search")
async def grok_search(q: str = Query(...), max_citations: int = Query(5, ge=1, le=10)):
    key = (
        os.getenv("XAI_API_KEY")
        or os.getenv("GROK_API_KEY")
        or os.getenv("xai_API_KEY")
    )
    if not key:
        raise HTTPException(503, "xAI API key missing")

    system = (
        "You are Grok with web access. Return STRICT JSON only with keys: "
        "query, summary (<=120 words), citations (array of {title,url,source})."
    )
    body = {
        "model": os.getenv("XAI_MODEL", "grok-beta"),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Research: {q}. Return JSON only."},
        ],
        "temperature": float(os.getenv("XAI_TEMPERATURE", "0.2")),
        "stream": False,
    }
    try:
        r = requests.post(
            os.getenv("GROK_ENDPOINT", "https://api.x.ai/v1/chat/completions"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=body,
            timeout=int(os.getenv("XAI_TIMEOUT", "60")),
        )
        if not r.ok:
            raise HTTPException(502, f"xAI error: {r.status_code}")
        raw = r.json()
        choices = raw.get("choices") or []
        if not choices:
            raise HTTPException(502, f"xAI empty response: {raw}")
        content = choices[0].get("message", {}).get("content")
        data = json.loads(content) if isinstance(content, str) else {}
        cites = data.get("citations") or []
        if len(cites) > max_citations:
            data["citations"] = cites[:max_citations]
        data.setdefault("query", q)
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"xAI call failed: {e}")
