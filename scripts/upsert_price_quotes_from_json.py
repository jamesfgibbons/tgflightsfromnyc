#!/usr/bin/env python3
"""
Insert parsed price quotes from JSON into Supabase table `price_quotes`.

Input JSON format:
  { "items": [ {"origin":"JFK","destination":"LAX","window_days":45,"price_low_usd":220,...}, ... ] }

Env:
  SUPABASE_URL, SUPABASE_SERVICE_ROLE (or SUPABASE_SERVICE_ROLE_KEY | SUPABASE_ANON_KEY)

Usage:
  python scripts/upsert_price_quotes_from_json.py --input data/price_quotes.json [--truncate]
"""
from __future__ import annotations
import argparse
import json
import os
from typing import Any, Dict, List

try:
    from supabase import create_client
except Exception:
    create_client = None  # type: ignore


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/price_quotes.json")
    ap.add_argument("--truncate", action="store_true", help="Delete existing rows before insert")
    args = ap.parse_args()

    data = json.load(open(args.input, "r", encoding="utf-8"))
    items: List[Dict[str, Any]] = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise SystemExit("Invalid input JSON: expected {items: []}")

    sb = get_client()
    if args.truncate:
        sb.table("price_quotes").delete().gt("created_at", "1900-01-01").execute()

    inserted = 0
    for i in range(0, len(items), 500):
        chunk = items[i : i + 500]
        sb.table("price_quotes").insert(chunk).execute()
        inserted += len(chunk)

    print({"ok": True, "inserted": inserted, "table": "price_quotes", "input": args.input})


if __name__ == "__main__":
    main()
