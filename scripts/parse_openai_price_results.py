#!/usr/bin/env python3
"""
Scan OpenAI cache for price_query records, parse into structured rows, and export CSV/JSON.
Optionally insert into Supabase (table: enrichment_results or price_quotes).
"""
from __future__ import annotations
import argparse
import csv
import glob
import json
import os
from typing import Any, Dict, List

from src.enrich.price_parser import parse_price_record


def iter_cache():
    for p in glob.glob('serpradio_convo_cache/openai_*.json'):
        try:
            rec=json.load(open(p,'r',encoding='utf-8'))
            rec['__file']=p
            yield rec
        except Exception:
            continue


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-json', default='data/price_quotes.json')
    ap.add_argument('--out-csv', default='data/price_quotes.csv')
    ap.add_argument('--to-supabase', action='store_true', help='Insert parsed rows into Supabase price_quotes')
    args = ap.parse_args()

    rows: List[Dict[str, Any]] = []
    for rec in iter_cache():
        meta = rec.get('metadata') or {}
        kind = (meta.get('kind') or '').lower()
        prompt = rec.get('prompt','')
        if kind != 'price_query':
            # Heuristic fallback for older cache entries
            if 'typical price of a flight' not in prompt:
                continue
        data = parse_price_record(rec)
        if not data:
            continue
        rows.append(data)

    os.makedirs(os.path.dirname(args.out_json) or '.', exist_ok=True)
    json.dump({'total': len(rows), 'items': rows}, open(args.out_json,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
    with open(args.out_csv,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=['origin','destination','window_days','price_low_usd','price_high_usd','typical_airlines','cited_websites','brands','notes'])
        w.writeheader()
        for r in rows:
            w.writerow({k: (', '.join(r[k]) if isinstance(r.get(k), list) else r.get(k)) for k in w.fieldnames})
    if args.to_supabase and rows:
        try:
            from src.storage import get_supabase_client, get_storage_backend
            if get_storage_backend()=='supabase':
                sb=get_supabase_client()
                # Insert in chunks
                for i in range(0, len(rows), 500):
                    chunk=rows[i:i+500]
                    sb.table('price_quotes').insert(chunk).execute()
        except Exception as e:
            print({'warn':'supabase_insert_failed','error':str(e)})
    print({'ok': True, 'parsed': len(rows), 'out_json': args.out_json, 'out_csv': args.out_csv, 'to_supabase': bool(args.to_supabase)})


if __name__=='__main__':
    main()
