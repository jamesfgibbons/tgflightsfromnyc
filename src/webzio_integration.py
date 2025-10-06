"""
Webz.io Firehose integration (stream consumer → Supabase + board dataset updater).

This module provides a lightweight consumer that connects to Webz.io Firehose
(HTTP streaming), parses events, and updates:

- Supabase table (optional): `webzio_events` with normalized event records
- Local dataset JSON compatible with /api/board/feed (optional)

Configure via environment variables (see README):
- WEBZIO_API_TOKEN (required)
- WEBZIO_FIREHOSE_URL (default: https://webz.io/fhose)
- WEBZIO_FILTER (optional; query string for filtering)
- WEBZIO_OUTPUT_DATASET_PATH (optional; path to write dataset JSON)
"""
from __future__ import annotations
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import requests

from .db import supabase_insert


DEFAULT_URL = "https://webz.io/fhose"


@dataclass
class WebzioConfig:
    api_token: str
    url: str = DEFAULT_URL
    filter: Optional[str] = None
    timeout: int = 60
    retries: int = 0  # 0 = infinite
    backoff_sec: float = 2.0
    dataset_path: Optional[str] = None


def load_config_from_env() -> WebzioConfig:
    token = os.getenv("WEBZIO_API_TOKEN")
    if not token:
        raise RuntimeError("WEBZIO_API_TOKEN not set")
    return WebzioConfig(
        api_token=token,
        url=os.getenv("WEBZIO_FIREHOSE_URL", DEFAULT_URL),
        filter=os.getenv("WEBZIO_FILTER"),
        timeout=int(os.getenv("WEBZIO_TIMEOUT", "60")),
        retries=int(os.getenv("WEBZIO_RETRIES", "0")),
        backoff_sec=float(os.getenv("WEBZIO_BACKOFF_SEC", "2.0")),
        dataset_path=os.getenv("WEBZIO_OUTPUT_DATASET_PATH"),
    )


def _build_params(cfg: WebzioConfig) -> Dict[str, Any]:
    params: Dict[str, Any] = {"token": cfg.api_token}
    if cfg.filter:
        params["q"] = cfg.filter
    return params


def stream_events(cfg: WebzioConfig) -> Iterable[Dict[str, Any]]:
    """Yield JSON events from Webz.io Firehose with reconnection/backoff."""
    attempt = 0
    while True:
        try:
            with requests.get(
                cfg.url,
                params=_build_params(cfg),
                stream=True,
                timeout=cfg.timeout,
            ) as r:
                r.raise_for_status()
                for line in r.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    try:
                        yield json.loads(line)
                    except Exception:
                        # ignore malformed lines
                        continue
        except Exception:
            attempt += 1
            if cfg.retries and attempt > cfg.retries:
                break
            time.sleep(min(60.0, cfg.backoff_sec * attempt))


def normalize_event(e: Dict[str, Any]) -> Dict[str, Any]:
    """Extract a compact event record for storage/analytics.

    This is best-effort; Webz.io schema may include fields like:
    title, author, domain, site_type, language, published, crawled, entities, rating, country, etc.
    """
    return {
        "title": e.get("title") or e.get("thread", {}).get("title"),
        "url": e.get("url"),
        "site": (e.get("thread", {}) or {}).get("site_full") or e.get("site_full"),
        "published_at": e.get("published") or e.get("thread", {}).get("published") or e.get("crawled") or e.get("timestamp"),
        "country": (e.get("thread", {}) or {}).get("country"),
        "language": e.get("language"),
        "rating": e.get("rating") or (e.get("thread", {}) or {}).get("social", {}),
        "entities": e.get("entities") or {},
        "categories": e.get("categories") or [],
        "source": e.get("source") or "webzio",
        "raw": e,
    }


def compute_scores(ev: Dict[str, Any]) -> Dict[str, float]:
    """Placeholder scoring for deal/novelty/brand/region preferences.

    Replace with domain logic or ML later. Keep keys consistent with frontend.
    """
    title = (ev.get("title") or "").lower()
    site = (ev.get("site") or "").lower()
    # naive signals
    novelty = 0.6 if "breaking" in title or "exclusive" in title else 0.3
    brand = 0.7 if any(b in site for b in ("skyscanner", "expedia", "booking")) else 0.4
    region = 0.5  # TODO: derive from country/language
    deal = 0.6 if any(k in title for k in ("deal", "cheap", "sale")) else 0.3
    return {
        "novelty_score": novelty,
        "brand_pref_score": brand,
        "region_pref_score": region,
        "deal_score": deal,
    }


def write_board_dataset(path: str, events: List[Dict[str, Any]], max_items: int = 20) -> None:
    """Write a simple board-compatible dataset JSON from recent events.

    Structure includes: time_series (placeholder), entities_top/keywords_top (from titles/sites).
    This keeps /api/board/feed usable via `?dataset=...`.
    """
    # Build keyword/entity buckets from titles/sites
    keywords: List[Dict[str, Any]] = []
    entities: List[Dict[str, Any]] = []
    for ev in events[:max_items]:
        scores = ev.get("scores") or {}
        title = ev.get("title") or "untitled"
        site = ev.get("site") or "unknown"
        keywords.append({
            "keyword": title,
            "organic_traffic": int(1000 * scores.get("deal_score", 0.3)),  # synthetic weight
            "serp_features": [],
            "updated": ev.get("published_at") or "",
        })
        entities.append({
            "name": site,
            "traffic": int(1000 * scores.get("brand_pref_score", 0.4)),
        })

    dataset = {
        "source": "webzio_firehose",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "time_series": [],
        "latest_summary": {},
        "positions_and_serp": {},
        "entities_top": entities,
        "keywords_top": keywords,
        "serp_feature_counts_top": [],
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)


def run_consumer_loop(cfg: WebzioConfig) -> None:
    """Start streaming, store to Supabase, and update dataset periodically."""
    recent: List[Dict[str, Any]] = []
    for ev in stream_events(cfg):
        norm = normalize_event(ev)
        norm["scores"] = compute_scores(norm)
        # Best-effort Supabase insert
        try:
            supabase_insert("webzio_events", norm)
        except Exception:
            pass
        recent.insert(0, norm)
        recent = recent[:200]
        # Periodically write dataset for board feed usage
        if cfg.dataset_path and (len(recent) % 10 == 0):
            try:
                write_board_dataset(cfg.dataset_path, recent)
            except Exception:
                pass

