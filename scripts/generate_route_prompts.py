#!/usr/bin/env python3
"""
Generate prompt lists for canonical routes with seasonal/booking context.

Outputs either a JSON array of prompt strings (default) or posts them to the
intake endpoint `/api/intake/prompts` using INTAKE_TOKEN and BASE.

Sources:
- Supabase table `travel_routes_nyc` (default)
- Local cache JSON `data/routes_nyc_cache.json` (via --input)

Usage examples:
  # Write prompts file for 1k routes (JFK only), season hint Thanksgiving
  python scripts/generate_route_prompts.py \
    --limit 1000 --origin JFK --season "Thanksgiving week" \
    --window 60 --out config/daily_prompts.json

  # Post directly to intake
  BASE=http://localhost:8000 INTAKE_TOKEN=... \
  python scripts/generate_route_prompts.py --limit 300 --post-intake --source lovable.board
"""
from __future__ import annotations
import argparse
import json
import os
from typing import Any, Dict, List


def load_routes_from_cache(path: str, limit: int | None, origin: str | None) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("items") or []
    if origin:
        items = [it for it in items if (it.get("origin") or "").upper() == origin.upper()]
    if limit and limit > 0:
        items = items[:limit]
    return items


def load_routes_from_supabase(limit: int | None, origin: str | None) -> List[Dict[str, Any]]:
    try:
        from src.storage import get_supabase_client, get_storage_backend
        if get_storage_backend() != "supabase":
            return []
        sb = get_supabase_client()
        q = sb.table("travel_routes_nyc").select("origin,destination,destination_name").order("created_at")
        if origin:
            q = q.eq("origin", origin.upper())
        if limit and limit > 0:
            q = q.limit(limit)
        res = q.execute()
        return getattr(res, "data", []) or []
    except Exception:
        return []


def build_prompt(o: str, d: str, dname: str | None, season: str | None, window_days: int) -> str:
    route = f"{o} to {dname or d}" if dname else f"{o} to {d}"
    season_hint = f" for {season.strip()}" if season else ""
    return (
        f"When is the best time to book{season_hint} flights from {route}?\n"
        f"Return STRICT JSON: {{ \"origin\": \"{o}\", \"destination\": \"{d}\", \"window_days\": {window_days},"
        " \"best_window_days\": [min,max], \"fare_low_usd\": number, \"fare_high_usd\": number, \"notes\": string }}"
    )


HOLIDAY_DEFAULTS = [
    "Thanksgiving week",
    "Christmas week",
    "New Year's week",
    "Spring Break",
    "Memorial Day weekend",
    "Fourth of July",
    "Labor Day weekend",
    "Summer peak (July)",
]


def build_mixed_prompts(o: str, d: str, dname: str | None, window_days: int, holidays: list[str]) -> list[str]:
    """Generate a small mix of prompt variants for the route.

    Includes: generic best-time-to-book, several holiday-focused prompts, and a weekend-trip variant.
    """
    route = f"{o} to {dname or d}" if dname else f"{o} to {d}"
    prompts: list[str] = []
    # Generic
    prompts.append(
        build_prompt(o, d, dname, None, window_days)
    )
    # Holidays
    for h in holidays:
        prompts.append(build_prompt(o, d, dname, h, window_days))
    # Weekend trip
    prompts.append(
        (
            f"When is the best time to book a weekend trip from {route} (Fri evening to Sun night)"
            f" within the next {window_days} days?\n"
            f"Return STRICT JSON: {{ \"origin\": \"{o}\", \"destination\": \"{d}\", \"window_days\": {window_days},"
            " \"best_window_days\": [min,max], \"fare_low_usd\": number, \"fare_high_usd\": number, \"notes\": string }}"
        )
    )
    return prompts


def post_intake(items: List[str], source: str) -> Dict[str, Any]:
    import requests
    base = os.getenv("BASE", "http://localhost:8000")
    token = os.getenv("INTAKE_TOKEN")
    if not token:
        raise SystemExit("Set INTAKE_TOKEN to post to /api/intake/prompts")
    payload = {
        "items": [{"source": source, "prompt": p, "metadata": {"kind": "best_time_to_book"}} for p in items]
    }
    r = requests.post(
        f"{base}/api/intake/prompts",
        headers={"Content-Type": "application/json", "X-Client-Token": token},
        json=payload,
        timeout=60,
    )
    try:
        return r.json()
    except Exception:
        return {"status_code": r.status_code}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="Optional routes cache JSON")
    ap.add_argument("--origin", help="Filter JFK|LGA|EWR", default=None)
    ap.add_argument("--limit", type=int, default=1000)
    ap.add_argument("--season", help="Seasonal hint (e.g., Thanksgiving week)", default=None)
    ap.add_argument("--window", type=int, default=60)
    ap.add_argument("--out", help="Write JSON array to this path")
    ap.add_argument("--post-intake", action="store_true", help="POST to /api/intake/prompts")
    ap.add_argument("--source", default="lovable.board", help="Source tag for intake")
    ap.add_argument("--mix", action="store_true", help="Generate a mix of prompts (holidays + generic + weekend)")
    ap.add_argument("--holidays", nargs="*", help="Holiday labels (default set if omitted)")
    ap.add_argument("--unique-only", dest="unique_only", action="store_true", help="Deduplicate routes by (origin,destination) before generating prompts")
    ap.add_argument("--max-per-route", type=int, default=10, help="Cap prompts per unique route in mix mode (default 10)")
    args = ap.parse_args()

    if args.input:
        rows = load_routes_from_cache(args.input, args.limit, args.origin)
    else:
        rows = load_routes_from_supabase(args.limit, args.origin)
    # Optionally dedupe unique routes before prompt generation
    if args.unique_only:
        seen=set()
        uniq=[]
        for it in rows:
            o=(it.get("origin") or "").upper()
            d=(it.get("destination") or "").upper()
            if not (o and d):
                continue
            k=(o,d)
            if k in seen:
                continue
            seen.add(k)
            uniq.append(it)
        rows=uniq
    if not rows:
        raise SystemExit("No routes found. Provide --input cache or configure Supabase.")

    prompts: List[str] = []
    for it in rows:
        o = (it.get("origin") or "").upper()
        d = (it.get("destination") or "").upper()
        dn = it.get("destination_name")
        if not (o and d):
            continue
        if args.mix:
            hols = args.holidays if args.holidays else HOLIDAY_DEFAULTS
            per_route = build_mixed_prompts(o, d, dn, args.window, hols)
            if args.max_per_route and args.max_per_route > 0:
                per_route = per_route[: args.max_per_route]
            prompts.extend(per_route)
        else:
            prompts.append(build_prompt(o, d, dn, args.season, args.window))

    # Final de-duplication to avoid wasted calls
    before=len(prompts)
    prompts=list(dict.fromkeys(prompts))  # preserves order
    after=len(prompts)

    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(prompts, f, ensure_ascii=False, indent=2)
        print(f"Wrote {len(prompts)} prompts to {args.out}")

    if args.post_intake:
        res = post_intake(prompts, args.source)
        print(res)


if __name__ == "__main__":
    main()
