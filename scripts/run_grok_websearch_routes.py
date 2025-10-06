#!/usr/bin/env python3
"""
Run Grok websearch for top routes to gather recent context with citations.

Reads routes from Supabase table `travel_routes_nyc` (or a local canonical JSON)
and for each route constructs a query like:
  "recent news and factors impacting ORIGIN→DEST in the next 45 days"

Stores raw results in `llm_results` via xAI cache helper. Optionally writes a
summary JSON for quick inspection.

Usage:
  PYTHONPATH=. python scripts/run_grok_websearch_routes.py \
    --limit 50 --window 45 --out data/grok_websearch_routes.json

  # From local file instead of Supabase
  PYTHONPATH=. python scripts/run_grok_websearch_routes.py \
    --input data/routes_nyc_canonical.json --limit 50 --window 45
"""
from __future__ import annotations
import argparse
import json
import os
import time
from typing import Any, Dict, List

from src.llm_xai import call_xai_with_cache


def load_routes(limit: int, path: str | None = None) -> List[Dict[str, Any]]:
    if path:
        data = json.load(open(path, 'r', encoding='utf-8'))
        items = data.get('items') or []
        items = items[:limit]
        return items
    # From Supabase if configured
    try:
        from src.storage import get_supabase_client, get_storage_backend
        if get_storage_backend() != 'supabase':
            return []
        sb = get_supabase_client()
        # Order by popularity_score desc if available
        res = sb.table('travel_routes_nyc').select('origin,destination,destination_name,popularity_score').order('popularity_score', desc=True).limit(limit).execute()
        return getattr(res, 'data', []) or []
    except Exception:
        return []


def build_query(o: str, d: str, dname: str | None, window_days: int) -> str:
    name = dname or d
    return (
        f"Recent news and factors impacting flights from {o} to {name} in the next {window_days} days.\n"
        "Include: price/availability trends, strikes/airline ops, weather or seasonal effects, big events, and travel advisories."
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=50)
    ap.add_argument('--window', type=int, default=45)
    ap.add_argument('--input', type=str, default=None, help='Optional canonical routes JSON')
    ap.add_argument('--out', type=str, default='data/grok_websearch_routes.json')
    ap.add_argument('--sleep', type=float, default=0.2)
    args = ap.parse_args()

    routes = load_routes(args.limit, args.input)
    if not routes:
        print({'ok': False, 'error': 'no routes found'})
        return

    results: List[Dict[str, Any]] = []
    for it in routes:
        o = (it.get('origin') or '').upper()
        d = (it.get('destination') or '').upper()
        dn = it.get('destination_name')
        if not (o and d):
            continue
        q = build_query(o, d, dn, args.window)
        system = (
            "You are Grok with web access. Perform up-to-date websearch and return STRICT JSON: "
            "{\"query\":str,\"summary\":str,\"citations\":[{\"title\":str,\"url\":str,\"source\":str}]}."
        )
        meta = {'kind': 'grok_search', 'origin': o, 'destination': d}
        rec = call_xai_with_cache(q, system=system, metadata=meta)
        results.append({'origin': o, 'destination': d, 'result': rec})
        time.sleep(args.sleep)

    os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
    json.dump({'total': len(results), 'items': results}, open(args.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print({'ok': True, 'saved': args.out, 'total': len(results)})


if __name__ == '__main__':
    main()

