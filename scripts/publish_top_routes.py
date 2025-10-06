#!/usr/bin/env python3
"""
Publish Top NYC routes (JFK/LGA/EWR) to Supabase table `travel_routes_nyc`.

Inputs:
  - destinations_by_popularity.csv with columns: dest,name,score
    (score can be search volume, pax, or composite)

Env:
  SUPABASE_URL, SUPABASE_SERVICE_ROLE (or SUPABASE_SERVICE_ROLE_KEY | SUPABASE_ANON_KEY)

Usage:
  python scripts/publish_top_routes.py \
    --input destinations_by_popularity.csv \
    --limit 1000 \
    --source seo_volume
"""
from __future__ import annotations
import argparse
import csv
import os
from typing import List, Tuple

try:
    from supabase import create_client
except Exception:
    create_client = None  # type: ignore

NYC_ORIGINS = ["JFK", "LGA", "EWR"]


def get_client():
    if not create_client:
        raise SystemExit("pip install supabase to use this script")
    url = os.getenv("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )
    if not (url and key):
        raise SystemExit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE(_KEY) or SUPABASE_ANON_KEY")
    return create_client(url, key)


def read_destinations(path: str) -> List[Tuple[str, str, float]]:
    rows: List[Tuple[str, str, float]] = []
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            dest = (row.get("dest") or "").strip().upper()
            name = (row.get("name") or "").strip()
            score_raw = row.get("score")
            if not dest or score_raw is None:
                continue
            try:
                score = float(str(score_raw).replace(",", ""))
            except ValueError:
                continue
            rows.append((dest, name, score))
    rows.sort(key=lambda x: x[2], reverse=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="CSV with dest,name,score")
    ap.add_argument("--limit", type=int, default=1000, help="Max total origin-dest rows to insert")
    ap.add_argument("--source", default="manual", help="Source label for popularity score")
    args = ap.parse_args()

    sb = get_client()
    dests = read_destinations(args.input)

    # Build origin-dest grid ordered by score
    rows = []
    for dest, name, score in dests:
        for o in NYC_ORIGINS:
            rows.append(
                {
                    "origin": o,
                    "destination": dest,
                    "destination_name": name,
                    "popularity_score": score,
                    "source": args.source,
                }
            )
    if args.limit and args.limit > 0:
        rows = rows[: args.limit]

    # Insert in chunks
    inserted = 0
    for i in range(0, len(rows), 500):
        chunk = rows[i : i + 500]
        sb.table("travel_routes_nyc").insert(chunk).execute()
        inserted += len(chunk)

    print({"ok": True, "inserted": inserted, "table": "travel_routes_nyc"})


if __name__ == "__main__":
    main()

