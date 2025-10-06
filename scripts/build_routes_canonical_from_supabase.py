#!/usr/bin/env python3
"""
Build canonical NYC routes list (JFK/LGA/EWR → popular destinations) from Supabase.

Reads table `travel_routes_nyc`, orders by popularity_score DESC, dedupes by
(origin, destination), caps to --limit (default 300), and writes
data/routes_nyc_canonical.json.

Env required: SUPABASE_URL + SUPABASE_SERVICE_ROLE (or ANON if public readable)
"""
from __future__ import annotations
import argparse
import json
import os
from collections import OrderedDict
from pathlib import Path


def fetch_routes(limit: int | None, origin: str | None):
    from src.storage import get_supabase_client
    sb = get_supabase_client()
    q = sb.table("travel_routes_nyc").select("origin,destination,destination_name,popularity_score").order(
        "popularity_score", desc=True
    )
    if origin:
        q = q.eq("origin", origin.upper())
    if limit and limit > 0:
        q = q.limit(limit)
    res = q.execute()
    return getattr(res, "data", []) or []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--origin", help="Optional origin filter JFK|LGA|EWR", default=None)
    ap.add_argument("--out", default="data/routes_nyc_canonical.json")
    args = ap.parse_args()

    rows = fetch_routes(None, args.origin)
    uniq: dict[tuple[str, str], dict] = OrderedDict()
    for r in rows:
        o = (r.get("origin") or "").upper()
        d = (r.get("destination") or "").upper()
        if not (o and d):
            continue
        k = (o, d)
        if k in uniq:
            continue
        uniq[k] = {
            "origin": o,
            "destination": d,
            "destination_name": r.get("destination_name") or d,
        }
        if len(uniq) >= args.limit:
            break

    items = list(uniq.values())
    Path(os.path.dirname(args.out) or ".").mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"total": len(items), "items": items}, f, ensure_ascii=False, indent=2)
    print({"ok": True, "total": len(items), "out": args.out})


if __name__ == "__main__":
    main()

