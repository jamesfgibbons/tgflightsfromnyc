#!/usr/bin/env python3
"""
Run OpenAI for route price prompts with cache + Supabase logging.

Reads routes from canonical JSON (or supplied routes JSON) and asks:
"what is the typical price of a flight from ORIGIN to DEST within next N days?"

Usage:
  PYTHONPATH=. python scripts/run_openai_routes_price.py --routes data/routes_nyc_canonical.json --limit 300 --window 45 --model gpt-4o-mini
"""
from __future__ import annotations
import argparse
import json
import os
import time
from typing import Any, Dict, List

from src.llm_openai import call_openai_with_cache
from src.db import supabase_insert


def load_routes(path: str) -> List[Dict[str, Any]]:
    data = json.load(open(path, 'r', encoding='utf-8'))
    return data.get('items') or []


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--routes', default='data/routes_nyc_canonical.json')
    ap.add_argument('--limit', type=int, default=300)
    ap.add_argument('--window', type=int, default=45)
    ap.add_argument('--model', type=str, default=None)
    args = ap.parse_args()

    rows = load_routes(args.routes)
    if args.limit and args.limit>0:
        rows = rows[:args.limit]

    # Create prompt_runs record (best-effort)
    run_id=None
    try:
        res=supabase_insert('prompt_runs', {'status':'running','notes':'openai_price_batch'})
        if res and isinstance(res,list) and res:
            run_id=res[0].get('id')
    except Exception:
        pass
    processed=0
    system = (
        "You are a concise travel analyst. Use historical patterns and general heuristics to summarize"
        " typical price ranges and airlines. Be conservative and DO NOT include citations beyond domain names."
    )
    for it in rows:
        o = (it.get('origin') or '').upper()
        d = (it.get('destination') or '').upper()
        dn = it.get('destination_name')
        if not (o and d):
            continue
        p = build_prompt(o,d,dn,args.window)
        meta = { 'kind': 'price_query', 'origin': o, 'destination': d }
        if run_id:
            meta['run_id']=run_id
        call_openai_with_cache(p, system=system, model=args.model, metadata=meta)
        processed+=1
        time.sleep(float(os.getenv('OPENAI_BATCH_SLEEP_SEC','0.1')))
    # Mark run completed
    try:
        from src.storage import get_supabase_client, get_storage_backend
        if run_id and get_storage_backend()=='supabase':
            sb=get_supabase_client()
            sb.table('prompt_runs').update({'status':'completed'}).eq('id', run_id).execute()
    except Exception:
        pass
    print({'ok': True, 'processed': processed, 'run_id': run_id})


if __name__=='__main__':
    main()
