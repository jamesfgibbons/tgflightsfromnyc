#!/usr/bin/env python3
"""
Run a routes-driven pipeline: read a CSV of routes (origin,destination[,title])
→ build LLM plans → render batch → publish catalog → export to Supabase (vibenet_*).

This is useful for large, curated route lists (e.g., top 1000, ski 500).

Env required:
  - SUPABASE_URL, SUPABASE_ANON_KEY, (optional) SUPABASE_SERVICE_ROLE for DB export
  - GROQ_API_KEY or OPENAI_API_KEY
  - STORAGE_BUCKET, PUBLIC_STORAGE_BUCKET

CSV columns:
  - origin,destination[,title]

Examples:
  python scripts/run_routes_pipeline.py \
    --input top_1000_routes.csv \
    --catalog-prefix catalog/travel/top_routes \
    --sub-theme top_routes \
    --limit 1000

  python scripts/run_routes_pipeline.py \
    --input ski_routes.csv \
    --catalog-prefix catalog/travel/ski_routes \
    --sub-theme ski_season \
    --limit 500
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime
from typing import List, Dict, Any

from src.pipeline.openai_client import FlightLLM
from src.pipeline.schemas import LLMFlightResult, SonifyPlan
from src.pipeline.sonify_batch import render_batch, publish_catalog
from src.pipeline.theme_manager import ThemeManager


def read_routes_csv(path: str, limit: int | None) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            o = (row.get("origin") or "").strip().upper()
            d = (row.get("destination") or "").strip().upper()
            if not (o and d):
                continue
            out.append({
                "origin": o,
                "destination": d,
                "title": (row.get("title") or f"{o}->{d}")
            })
            if limit and len(out) >= limit:
                break
    return out


def build_plans(routes: List[Dict[str, str]], sub_theme: str, theme: str = "flights_from_nyc", channel: str = "travel") -> List[Dict[str, Any]]:
    llm = FlightLLM()
    tm = ThemeManager()
    # Minimal config to drive mapping helpers
    config = {"sub_theme": sub_theme, "sound_pack_default": "Synthwave"}
    if sub_theme == "ski_season":
        config["sound_pack_default"] = "Arena Rock"

    plans: List[Dict[str, Any]] = []
    for idx, r in enumerate(routes):
        prompt = f"Find cheapest one-way {r['origin']} to {r['destination']} next 45 days; compare nonstop vs 1-stop; include fees"
        data = llm.analyze_prompt(prompt)
        res = LLMFlightResult(
            origin=r["origin"],
            destination=r["destination"],
            prompt=prompt,
            **data,
        )
        # Theme-aware segments
        segs = tm._bands_from_llm(res, config)  # type: ignore[attr-defined]
        label_summary = tm._label_summary(segs)  # type: ignore[attr-defined]
        sound_pack = tm.enhanced_nostalgia_mapping(config, res)
        tempo, bars = tm._theme_aware_energy(config, res)  # type: ignore[attr-defined]

        plan = SonifyPlan(
            sound_pack=sound_pack,
            total_bars=bars,
            tempo_base=tempo,
            key_hint=None,
            momentum=segs,
            label_summary=label_summary,
        )
        plans.append({
            "id": f"{channel}_{theme}_{sub_theme}_{idx}",
            "timestamp": datetime.utcnow().isoformat(),
            "channel": channel,
            "theme": theme,
            "sub_theme": sub_theme,
            "origin": r["origin"],
            "destination": r["destination"],
            "brand": res.carrier_likelihood[0] if res.carrier_likelihood else "",
            "title": r.get("title") or f"{r['origin']}->{r['destination']}",
            "prompt": prompt,
            "plan": plan.model_dump(),
        })
    return plans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="CSV with origin,destination[,title]")
    ap.add_argument("--catalog-prefix", required=True, help="catalog prefix, e.g., catalog/travel/top_routes")
    ap.add_argument("--sub-theme", default="top_routes")
    ap.add_argument("--theme", default="flights_from_nyc")
    ap.add_argument("--channel", default="travel")
    ap.add_argument("--limit", type=int, default=1000)
    args = ap.parse_args()

    routes = read_routes_csv(args.input, args.limit)
    plans = build_plans(routes, sub_theme=args.sub_theme, theme=args.theme, channel=args.channel)
    entries = render_batch(plans)
    publish_catalog(entries, catalog_prefix=args.catalog_prefix)

    print({
        "ok": True,
        "rendered": len(entries),
        "catalog": f"{args.catalog_prefix}/latest.json",
        "sub_theme": args.sub_theme,
    })


if __name__ == "__main__":
    main()

