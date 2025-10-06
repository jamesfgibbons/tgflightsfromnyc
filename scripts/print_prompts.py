#!/usr/bin/env python
"""
Print a prompt list (JSON or CSV) for a given vertical/theme/sub_theme using ThemeManager.
Example:
  python scripts/print_prompts.py --vertical travel --theme flights_from_nyc --sub-theme ski_season --limit 100 --format json
"""
import argparse
import csv
import json
import sys
from typing import Any, Dict, List

from src.pipeline.theme_manager import ThemeManager


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vertical", default="travel")
    ap.add_argument("--theme", default="flights_from_nyc")
    ap.add_argument("--sub-theme", default=None)
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--format", choices=["json", "csv"], default="json")
    args = ap.parse_args()

    tm = ThemeManager()
    prompts: List[Dict[str, Any]] = tm.build_prompts_for_theme(
        vertical=args.vertical, theme=args.theme, sub_theme=args.__dict__["sub_theme"], limit=args.limit
    )

    # Normalize fields we care about
    out = [
        {
            "origin": p.get("origin"),
            "destination": p.get("destination"),
            "title": p.get("title"),
            "prompt": p.get("prompt"),
            "theme": args.theme,
            "sub_theme": args.__dict__["sub_theme"],
        }
        for p in prompts
    ]

    if args.format == "json":
        print(json.dumps({"count": len(out), "items": out}, indent=2))
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=["origin", "destination", "title", "prompt", "theme", "sub_theme"])
        writer.writeheader()
        for row in out:
            writer.writerow(row)


if __name__ == "__main__":
    main()
