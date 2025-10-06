#!/usr/bin/env python3
"""
Publish ski destination list into Supabase `travel_routes_ski` with regional metadata.

Input CSV columns (header required):
  dest,name,region,subregion,country,state_province,score

The script expands rows across NYC origins (JFK,LGA,EWR) and inserts up to --limit.

Env:
  SUPABASE_URL, SUPABASE_SERVICE_ROLE (or *_KEY | SUPABASE_ANON_KEY)

Usage:
  python scripts/publish_ski_routes.py --input ski_destinations.csv --limit 500 --source curated
"""
from __future__ import annotations
import argparse
import csv
import os
from typing import List, Dict

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


def read_ski_csv(path: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            if not row.get("dest"):
                continue
            # Normalize
            row = {k: (v or "").strip() for k, v in row.items()}
            row["dest"] = row["dest"].upper()
            rows.append(row)
    # Sort by score desc if present
    def score(r):
        try:
            return float(str(r.get("score", "0").replace(",", "")))
        except ValueError:
            return 0.0
    rows.sort(key=score, reverse=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="CSV with dest,name,region,subregion,country,state_province,score")
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--source", default="manual")
    args = ap.parse_args()

    sb = get_client()
    dest_rows = read_ski_csv(args.input)

    to_insert: List[Dict[str, str]] = []
    for row in dest_rows:
        for o in NYC_ORIGINS:
            to_insert.append(
                {
                    "origin": o,
                    "destination": row.get("dest"),
                    "destination_name": row.get("name"),
                    "region": row.get("region"),
                    "subregion": row.get("subregion"),
                    "country": row.get("country"),
                    "state_province": row.get("state_province"),
                    "popularity_score": float(row.get("score") or 0) if str(row.get("score") or "").strip() else None,
                    "source": args.source,
                }
            )
    if args.limit and args.limit > 0:
        to_insert = to_insert[: args.limit]

    inserted = 0
    for i in range(0, len(to_insert), 500):
        chunk = to_insert[i : i + 500]
        sb.table("travel_routes_ski").insert(chunk).execute()
        inserted += len(chunk)

    print({"ok": True, "inserted": inserted, "table": "travel_routes_ski"})


if __name__ == "__main__":
    main()

