"""
Daily LLM Pipeline: fetch prompts and call xAI (Grok) with caching, store raw results.

Sources for prompts:
- Supabase table `api_results` with status='accepted' (best-effort)
- Fallback JSON file `config/daily_prompts.json` (array of strings)

Execution:
- Iterates prompts, calls `call_xai_with_cache`, and logs an audit row to Supabase `prompt_runs` (best-effort).
"""
from __future__ import annotations
import json
import os
import time
from typing import Any, Dict, List

from .llm_xai import call_xai_with_cache


def _load_prompts_from_file(path: str) -> List[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [{"prompt": str(p), "source": "file"} for p in data]
        return []
    except FileNotFoundError:
        return []


def _load_prompts_from_supabase(limit: int = 100) -> List[Dict[str, Any]]:
    try:
        from .storage import get_supabase_client, get_storage_backend
        if get_storage_backend() != "supabase":
            return []
        sb = get_supabase_client()
        # fetch accepted intake rows (most recent first)
        res = (
            sb.table("api_results")
            .select("id, source, request_payload")
            .eq("status", "accepted")
            .order("created_at", desc=True)  # may be ignored if column not present
            .limit(limit)
            .execute()
        )
        rows = getattr(res, "data", []) or []
        out: List[Dict[str, Any]] = []
        for r in rows:
            payload = r.get("request_payload") or {}
            p = payload.get("prompt")
            if not p:
                continue
            out.append({"prompt": p, "source": r.get("source") or "intake", "id": r.get("id")})
        return out
    except Exception:
        return []


def run_daily_xai(max_items: int = 50, model: str | None = None) -> Dict[str, Any]:
    prompts = _load_prompts_from_supabase(limit=max_items)
    if not prompts:
        prompts = _load_prompts_from_file(os.getenv("DAILY_PROMPTS_PATH", "config/daily_prompts.json"))
    if not prompts:
        return {"ok": False, "error": "no prompts found"}

    results: List[Dict[str, Any]] = []
    for i, item in enumerate(prompts[:max_items]):
        prompt = item.get("prompt", "").strip()
        if not prompt:
            continue
        meta = {"source": item.get("source"), "intake_id": item.get("id")}
        rec = call_xai_with_cache(prompt, system=os.getenv("DAILY_XAI_SYSTEM"), model=model, metadata=meta)
        results.append(rec)
        time.sleep(float(os.getenv("DAILY_XAI_SLEEP_SEC", "0.2")))

    # Best-effort audit record
    try:
        from .db import supabase_insert
        supabase_insert(
            "prompt_runs",
            {
                "count": len(results),
                "provider": "xai",
                "model": model or os.getenv("GROK_MODEL") or os.getenv("XAI_MODEL") or "grok-beta",
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        )
    except Exception:
        pass

    return {"ok": True, "processed": len(results)}

