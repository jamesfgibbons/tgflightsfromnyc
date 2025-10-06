"""
LLM client helpers for OpenAI with cache + Supabase persistence.

Functions:
- call_openai_with_cache(prompt, system=None, model=None, metadata=None)
  Returns dict: {provider, model, prompt, response_raw, latency_ms, status}

Caching:
- File cache directory: LLM_CACHE_DIR (shared with other providers)
- Cache key: sha1(provider|model|prompt|system)
- TTL hours optional: LLM_CACHE_TTL_HOURS; if set, ignores expired cache

Persistence:
- Inserts into Supabase table 'llm_results' when configured, best-effort.
"""
from __future__ import annotations
import hashlib
import json
import os
import time
from typing import Any, Dict, Optional

from openai import OpenAI

from .db import supabase_insert


def _cache_dir() -> str:
    return os.getenv("LLM_CACHE_DIR", "serpradio_convo_cache")


def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _cache_path(provider: str, model: str, prompt: str, system: Optional[str]) -> str:
    key = _sha1("|".join([provider, model or "", prompt or "", system or ""]))
    d = _cache_dir()
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{provider}_{model}_{key}.json")


def _read_cache(path: str) -> Optional[Dict[str, Any]]:
    try:
        ttl_hours = float(os.getenv("LLM_CACHE_TTL_HOURS", "0") or 0)
    except Exception:
        ttl_hours = 0.0
    try:
        st = os.stat(path)
        if ttl_hours > 0:
            age = time.time() - st.st_mtime
            if age > ttl_hours * 3600.0:
                return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def _write_cache(path: str, payload: Dict[str, Any]) -> None:
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def call_openai_with_cache(
    prompt: str,
    *,
    system: Optional[str] = None,
    model: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    provider = "openai"
    model = model or os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
    path = _cache_path(provider, model, prompt, system)
    cached = _read_cache(path)
    if cached:
        return cached

    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return {
            "provider": provider,
            "model": model,
            "prompt": prompt,
            "response_raw": {"error": "missing OPENAI_API_KEY"},
            "latency_ms": 0,
            "status": "skipped",
        }

    client = OpenAI(api_key=key)
    messages = ([{"role": "system", "content": system}] if system else []) + [
        {"role": "user", "content": prompt}
    ]
    t0 = time.time()
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.2")),
            messages=messages,
            response_format={"type": "json_object"},
        )
        latency = int((time.time() - t0) * 1000)
        status = "ok"
        raw = {
            "id": resp.id,
            "created": resp.created,
            "model": resp.model,
            "choices": [
                {"message": {"role": c.message.role, "content": c.message.content}}
                for c in resp.choices
            ],
        }
    except Exception as e:
        latency = int((time.time() - t0) * 1000)
        status = "error"
        raw = {"exception": str(e)}

    record = {
        "provider": provider,
        "model": model,
        "prompt": prompt,
        "response_raw": raw,
        "latency_ms": latency,
        "status": status,
        "metadata": metadata or {},
    }

    try:
        payload = {
            **record,
            "metadata": metadata or {},
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        # Promote run_id/list_item_id to top-level columns if provided
        if isinstance(metadata, dict):
            rid = metadata.get("run_id")
            if rid:
                payload["run_id"] = rid
            li = metadata.get("list_item_id")
            if li:
                payload["list_item_id"] = li
        supabase_insert("llm_results", payload)
    except Exception:
        pass

    if record["status"] == "ok":
        _write_cache(path, record)
    return record
