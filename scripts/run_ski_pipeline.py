#!/usr/bin/env python
"""
Ad hoc Groq/OpenAI pipeline to generate a top-100 set of ski-season prompts and render audio.
Publishes to catalog/travel/ski_season.
"""
import os
from typing import List, Dict, Any
from datetime import datetime

from src.pipeline.theme_manager import ThemeManager
from src.pipeline.sonify_batch import render_batch, publish_catalog


def main(limit: int = 100):
    tm = ThemeManager()
    plans: List[Dict[str, Any]] = tm.build_enhanced_plans(
        vertical="travel",
        theme="flights_from_nyc",
        sub_theme="ski_season",
        limit=limit,
    )
    entries = render_batch(plans)
    publish_catalog(entries, catalog_prefix="catalog/travel/ski_season")
    print(
        {
            "ok": True,
            "rendered": len(entries),
            "catalog": "catalog/travel/ski_season/latest.json",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100)
    args = ap.parse_args()
    main(args.limit)
