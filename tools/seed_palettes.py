#!/usr/bin/env python
"""
Seed vibe_palettes table from config/vibe_palettes.yaml using Supabase client if configured.
No external DB drivers required.
"""
import os
import sys
import json
import yaml

from src.db import supabase_insert


def main(path: str = "config/vibe_palettes.yaml") -> int:
    if not os.path.exists(path):
        print(f"Palette file not found: {path}", file=sys.stderr)
        return 1
    with open(path, "r") as f:
        palettes = yaml.safe_load(f) or []

    count = 0
    for p in palettes:
        rec = {
            "slug": p.get("slug"),
            "title": p.get("title"),
            "description": p.get("description"),
            "target_valence": p.get("target_valence"),
            "target_energy": p.get("target_energy"),
            "tempo_min": p.get("tempo_min"),
            "tempo_max": p.get("tempo_max"),
            "mode_preference": p.get("mode_preference"),
            "default_pack": p.get("default_pack"),
            "instrumentation_json": p.get("instrumentation_json"),
            "signature_rhythm_json": p.get("signature_rhythm_json"),
            "chord_blocks_json": p.get("chord_blocks_json"),
        }
        supabase_insert("vibe_palettes", rec)
        count += 1

    print(f"Seeded {count} palette records (if Supabase configured)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "config/vibe_palettes.yaml"))

