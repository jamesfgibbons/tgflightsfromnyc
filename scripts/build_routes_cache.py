#!/usr/bin/env python3
"""
Build a test cache for NYC routes (JFK/LGA/EWR × destinations) from a
`destinations_by_popularity.csv` file and write a JSON cache for quick local use.

Input CSV headers: dest,name,score
Output JSON: data/routes_nyc_cache.json with { total, items: [{origin,destination,destination_name,score}] }

Usage:
  python scripts/build_routes_cache.py --input destinations_by_popularity.csv --limit 5000 --out data/routes_nyc_cache.json
"""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

NYC_ORIGINS = ["JFK", "LGA", "EWR"]


def read_destinations(path: str):
    rows = []
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
    ap.add_argument("--input", required=True)
    ap.add_argument("--limit", type=int, default=5000)
    ap.add_argument("--out", default="data/routes_nyc_cache.json")
    args = ap.parse_args()

    dests = read_destinations(args.input)
    items = []
    for dest, name, score in dests:
        for o in NYC_ORIGINS:
            items.append({
                "origin": o,
                "destination": dest,
                "destination_name": name,
                "score": score,
            })
    if args.limit and args.limit > 0:
        items = items[: args.limit]

    out = {"total": len(items), "items": items}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(items)} routes to {args.out}")


if __name__ == "__main__":
    main()

