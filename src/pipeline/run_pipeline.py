"""
CLI entrypoint: build plans from themes, render batch, publish catalog.
Enhanced for multi-theme NYC flights focus.
"""
import os, argparse, json
from typing import List, Dict, Any

from .theme_manager import ThemeManager
from .sonify_batch import render_batch, publish_catalog

def main():
    ap = argparse.ArgumentParser(description="SERP Radio Pipeline - NYC Flights Focus")
    ap.add_argument("--limit", type=int, default=30, help="Total tracks to generate")
    ap.add_argument("--vertical", default="travel", help="Vertical to run (travel, finance, etc.)")
    ap.add_argument("--theme", default="flights_from_nyc", help="Theme within vertical")
    ap.add_argument("--sub-themes", nargs="+", 
                   default=[
                       "budget_carriers",
                       "legacy_airlines",
                       "red_eye_deals",
                       "caribbean_kokomo",
                       "non_brand_seo",
                       "best_time_to_book",
                       "hidden_city_hacks",
                       "weekend_getaways"
                   ],
                   help="Sub-themes to include")
    ap.add_argument("--tracks-per-theme", type=int, default=10, help="Tracks per sub-theme")
    args = ap.parse_args()

    print(f"🎵 SERP Radio Pipeline: {args.vertical}/{args.theme}")
    print(f"📊 Generating {args.tracks_per_theme} tracks per theme")
    print(f"🎯 Sub-themes: {', '.join(args.sub_themes)}")
    
    # Initialize theme manager
    theme_manager = ThemeManager()
    
    all_plans: List[Dict[str, Any]] = []
    
    # Generate plans for each sub-theme
    for sub_theme in args.sub_themes:
        print(f"\n🔄 Processing theme: {sub_theme}")
        try:
            plans = theme_manager.build_enhanced_plans(
                vertical=args.vertical,
                theme=args.theme,
                sub_theme=sub_theme,
                limit=args.tracks_per_theme
            )
            all_plans.extend(plans)
            print(f"✅ Generated {len(plans)} plans for {sub_theme}")
        except Exception as e:
            print(f"❌ Failed to process {sub_theme}: {e}")
            continue
    
    # Limit total if specified
    if args.limit and len(all_plans) > args.limit:
        all_plans = all_plans[:args.limit]
        print(f"📊 Limited to {args.limit} total tracks")
    
    print(f"\n🎼 Rendering {len(all_plans)} total tracks...")
    
    # Render audio and publish catalog
    entries = render_batch(all_plans)
    publish_catalog(entries, catalog_prefix=f"catalog/{args.vertical}/{args.theme}")
    
    # Summary
    theme_summary = {}
    for entry in entries:
        theme_key = f"{entry.brand}_{getattr(entry, 'sub_theme', 'unknown')}"
        theme_summary[theme_key] = theme_summary.get(theme_key, 0) + 1
    
    result = {
        "ok": True,
        "rendered": len(entries),
        "vertical": args.vertical,
        "theme": args.theme,
        "sub_themes_processed": args.sub_themes,
        "theme_breakdown": theme_summary
    }
    
    print(json.dumps(result, indent=2))
    return result

if __name__ == "__main__":
    main()
