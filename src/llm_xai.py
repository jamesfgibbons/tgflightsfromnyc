"""
LLM client helpers for xAI Grok (preferred), with cache + Supabase persistence.

Functions:
- call_xai_with_cache(prompt, system=None, model=None, metadata=None)
  Returns dict: {provider, model, prompt, response_raw, latency_ms, status}

Caching:
- File cache directory: LLM_CACHE_DIR (default: serpradio_convo_cache)
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

import requests

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


def _xai_headers() -> Optional[Dict[str, str]]:
    # Accept common variants to reduce misconfig friction
    key = (
        os.getenv("GROK_API_KEY")
        or os.getenv("XAI_API_KEY")
        or os.getenv("xai_API_KEY")  # legacy lowercase seen in some envs
    )
    if not key:
        return None
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def call_xai_with_cache(
    prompt: str,
    *,
    system: Optional[str] = None,
    model: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    provider = "xai"
    model = model or os.getenv("GROK_MODEL") or os.getenv("XAI_MODEL") or "grok-beta"
    path = _cache_path(provider, model, prompt, system)
    cached = _read_cache(path)
    if cached:
        return cached

    headers = _xai_headers()
    if not headers:
        # No xAI key; return a stub and do not cache
        return {
            "provider": provider,
            "model": model,
            "prompt": prompt,
            "response_raw": {"error": "missing GROK/XAI API key"},
            "latency_ms": 0,
            "status": "skipped",
        }

    url = os.getenv("GROK_ENDPOINT", "https://api.x.ai/v1/chat/completions")
    body = {
        "model": model,
        "messages": (
            ([{"role": "system", "content": system}] if system else [])
            + [{"role": "user", "content": prompt}]
        ),
        "temperature": float(os.getenv("XAI_TEMPERATURE", "0.2")),
        "stream": False,
    }

    t0 = time.time()
    try:
        r = requests.post(url, headers=headers, json=body, timeout=int(os.getenv("XAI_TIMEOUT", "60")))
        latency = int((time.time() - t0) * 1000)
        status = "ok" if r.ok else "error"
        resp = r.json() if r.content else {"status_code": r.status_code}
    except Exception as e:
        latency = int((time.time() - t0) * 1000)
        status = "error"
        resp = {"exception": str(e)}

    record = {
        "provider": provider,
        "model": model,
        "prompt": prompt,
        "response_raw": resp,
        "latency_ms": latency,
        "status": status,
    }

    # Persist to Supabase (best-effort)
    try:
        payload = {
            **record,
            "metadata": metadata or {},
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
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

    # Cache only if success
    if record["status"] == "ok":
        _write_cache(path, record)
    return record
