#!/usr/bin/env python3
"""
Batch pipeline: OpenAI (cheap) 'best time to book' for canonical NYC routes.

Loads routes from Supabase table `travel_routes_nyc` or a local cache JSON,
builds prompts per origin-destination, calls OpenAI with cache, and stores raw
results to Supabase `llm_results` (best-effort).

Usage examples:
  # From Supabase (requires SUPABASE_URL + key)
  python scripts/run_openai_routes_booking.py --limit 500 --origin JFK

  # From local cache
  python scripts/run_openai_routes_booking.py --input data/routes_nyc_cache.json --limit 500
"""
from __future__ import annotations
import argparse
import json
import os
import time
from typing import Any, Dict, List

from src.llm_openai import call_openai_with_cache
from src.db import supabase_insert


def load_routes_from_cache(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items") or []
    # Expect fields: origin, destination, destination_name
    return items


def load_routes_from_supabase(limit: int, origin: str | None) -> List[Dict[str, Any]]:
    try:
        from src.storage import get_supabase_client, get_storage_backend
        if get_storage_backend() != "supabase":
            return []
        sb = get_supabase_client()
        q = sb.table("travel_routes_nyc").select("origin,destination,destination_name,popularity_score").limit(limit)
        if origin:
            q = q.eq("origin", origin.upper())
        res = q.execute()
        return getattr(res, "data", []) or []
    except Exception:
        return []


def prompt_for_route(origin: str, destination: str, window_days: int) -> str:
    return (
        f"Best time to book {origin}→{destination} within next {window_days} days.\n"
        "Include: fare ranges (USD), typical booking window (days before departure),\n"
        "peak/holiday effects, basic bag policy differences, and 1–2 concrete examples.\n"
        "Return STRICT JSON: {\n"
        "  \"origin\": string, \"destination\": string, \"window_days\": number,\n"
        "  \"best_window_days\": [min,max], \"fare_low_usd\": number, \"fare_high_usd\": number,\n"
        "  \"notes\": string\n"
        "}"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="Optional routes cache JSON {total,items}")
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--origin", type=str, default=None, help="Filter origin JFK|LGA|EWR")
    ap.add_argument("--window", type=int, default=60, help="Booking window days")
    ap.add_argument("--model", type=str, default=None, help="Override OPENAI_TEXT_MODEL")
    args = ap.parse_args()

    # Load routes
    items: List[Dict[str, Any]]
    if args.input:
        items = load_routes_from_cache(args.input)
    else:
        items = load_routes_from_supabase(args.limit, args.origin)
    if args.limit and args.limit > 0:
        items = items[: args.limit]

    system = (
        "You are a concise travel analyst. Use historical patterns and general heuristics to summarize\n"
        "booking timing and fare ranges. Be conservative, avoid hallucination, and DO NOT include citations."
    )

    # Create a prompt_runs record (best-effort)
    run_id = None
    try:
        res = supabase_insert('prompt_runs', { 'status': 'running', 'notes': 'openai_booking_batch' })
        if res and isinstance(res, list) and res:
            run_id = res[0].get('id')
    except Exception:
        pass

    processed = 0
    for it in items:
        o = (it.get("origin") or "").upper()
        d = (it.get("destination") or "").upper()
        if not (o and d):
            continue
        p = prompt_for_route(o, d, args.window)
        meta = {"kind": "best_time_to_book", "origin": o, "destination": d}
        if run_id:
            meta['run_id'] = run_id
        rec = call_openai_with_cache(p, system=system, model=args.model, metadata=meta)
        processed += 1
        time.sleep(float(os.getenv("OPENAI_BATCH_SLEEP_SEC", "0.1")))
    # Mark run completed
    try:
        from src.storage import get_supabase_client, get_storage_backend
        if run_id and get_storage_backend() == 'supabase':
            sb = get_supabase_client()
            sb.table('prompt_runs').update({'status': 'completed'}).eq('id', run_id).execute()
    except Exception:
        pass
    print({"ok": True, "processed": processed, "run_id": run_id})


if __name__ == "__main__":
    main()
