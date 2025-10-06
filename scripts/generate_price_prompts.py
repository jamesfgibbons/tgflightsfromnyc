#!/usr/bin/env python3
"""
Generate route price prompts: "what is the price of a flight from ORIGIN to DEST?" style.

Outputs a JSON array of prompt strings or posts to /api/intake/prompts.

Sources:
- Canonical cache JSON: data/routes_nyc_canonical.json (default)
- Any routes JSON with {items:[{origin,destination,destination_name?}]}
"""
from __future__ import annotations
import argparse
import json
import os
from typing import Any, Dict, List


def load_routes(path: str) -> List[Dict[str, Any]]:
    data = json.load(open(path, 'r', encoding='utf-8'))
    items = data.get('items') or []
    return items


def build_prompt(o: str, d: str, dname: str | None, window_days: int) -> str:
    route = f"{o} to {dname or d}" if dname else f"{o} to {d}"
    return (
        f"What is the typical price of a flight from {route} within the next {window_days} days?\n"
        "Return STRICT JSON: { \n"
        f"  \"origin\": \"{o}\", \"destination\": \"{d}\", \"window_days\": {window_days},\n"
        "  \"price_low_usd\": number, \"price_high_usd\": number,\n"
        "  \"typical_airlines\": [string], \"cited_websites\": [string], \"notes\": string\n"
        "}"
    )


def post_intake(prompts: List[str], source: str) -> Dict[str, Any]:
    import requests
    base = os.getenv('BASE', 'http://localhost:8000')
    token = os.getenv('INTAKE_TOKEN')
    if not token:
        raise SystemExit('Set INTAKE_TOKEN to post to /api/intake/prompts')
    payload = {
        'items': [{ 'source': source, 'prompt': p, 'metadata': { 'kind': 'price_query' } } for p in prompts]
    }
    r = requests.post(f"{base}/api/intake/prompts", headers={'Content-Type':'application/json','X-Client-Token':token}, json=payload, timeout=60)
    try:
        return r.json()
    except Exception:
        return {'status_code': r.status_code}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--routes', default='data/routes_nyc_canonical.json')
    ap.add_argument('--limit', type=int, default=300)
    ap.add_argument('--window', type=int, default=45)
    ap.add_argument('--out', help='Write prompts JSON array')
    ap.add_argument('--post-intake', action='store_true')
    ap.add_argument('--source', default='lovable.board')
    args = ap.parse_args()

    rows = load_routes(args.routes)
    if args.limit and args.limit>0:
        rows = rows[:args.limit]
    prompts: List[str] = []
    for it in rows:
        o = (it.get('origin') or '').upper()
        d = (it.get('destination') or '').upper()
        dn = it.get('destination_name')
        if not (o and d):
            continue
        prompts.append(build_prompt(o, d, dn, args.window))

    if args.out:
        os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
        json.dump(prompts, open(args.out,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
        print(f"Wrote {len(prompts)} prompts to {args.out}")
    if args.post_intake:
        res = post_intake(prompts, args.source)
        print(res)


if __name__ == '__main__':
    main()

