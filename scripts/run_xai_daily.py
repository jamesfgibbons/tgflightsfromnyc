#!/usr/bin/env python3
"""
Run the daily xAI (Grok) pipeline.

Usage:
  GROK_API_KEY=... python scripts/run_xai_daily.py --limit 50 --model grok-beta

Optionally set DAILY_PROMPTS_PATH to a JSON array of prompt strings if Supabase intake is unavailable.
"""
from __future__ import annotations
import argparse
from src.llm_pipeline import run_daily_xai


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--model", type=str, default=None)
    args = ap.parse_args()
    res = run_daily_xai(max_items=args.limit, model=args.model)
    print(res)


if __name__ == "__main__":
    main()

