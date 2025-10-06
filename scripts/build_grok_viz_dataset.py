import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

import pandas as pd


def _rename_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip() for c in df.columns]
    rename_map: Dict[str, str] = {}
    for c in df.columns:
        lc = c.lower()
        if lc == "date":
            rename_map[c] = "date"
        elif lc.startswith("organic pages"):
            rename_map[c] = "organic_pages"
        elif lc.startswith("organic traffic"):
            rename_map[c] = "organic_traffic"
        elif lc.startswith("organic positions: 1"):
            rename_map[c] = "positions_top3"
        elif lc.startswith("organic positions: 4"):
            rename_map[c] = "positions_4_10"
        elif lc.startswith("serp features: featured snippet"):
            rename_map[c] = "sf_featured_snippet"
        elif lc.startswith("serp features: people also ask"):
            rename_map[c] = "sf_people_also_ask"
        elif lc.startswith("serp features: sitelinks"):
            rename_map[c] = "sf_sitelinks"
        elif lc.startswith("serp features: video preview"):
            rename_map[c] = "sf_video_preview"
        elif lc.startswith("serp features: thumbnail"):
            rename_map[c] = "sf_thumbnail"
    if rename_map:
        df = df.rename(columns=rename_map)
    return df


def load_time_series(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = _rename_cols(df)
    if "date" not in df.columns:
        raise ValueError(f"Expected 'Date' column in {path}")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    # Ensure numeric
    for col in ("organic_pages", "organic_traffic"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_detailed_metrics(path: Path) -> pd.DataFrame:
    # This CSV contains header + 'Volume' + 'Location' rows; filter them out
    df_full = pd.read_csv(path)
    df_full = _rename_cols(df_full)
    # Drop meta rows
    df = df_full[~df_full.iloc[:, 0].astype(str).str.lower().isin(["volume", "location"])].copy()
    # Coerce date
    df["date"] = pd.to_datetime(df.iloc[:, 0], errors="coerce")
    df = df.dropna(subset=["date"])  # keep only data rows
    df = df.sort_values("date").reset_index(drop=True)
    return df


def load_keywords_orga(path: Path) -> pd.DataFrame:
    # UTF-16 with tab separators
    df = pd.read_csv(path, sep="\t", encoding="utf-16")
    # Normalize column names
    df.columns = [c.strip().strip("\ufeff").lower().replace(" ", "_") for c in df.columns]
    # Expected columns (best-effort): keyword, serp_features, volume, kd, cpc, organic_traffic, current_position, current_url, updated, navigational, informational, commercial, transactional, branded, local
    # Numeric fields
    for col in ["volume", "kd", "cpc", "organic_traffic", "paid_traffic", "current_position"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # Boolean-ish intent fields
    intent_cols = [
        "navigational",
        "informational",
        "commercial",
        "transactional",
        "branded",
        "local",
    ]
    for col in intent_cols:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.strip()
                .str.lower()
                .isin(["true", "1", "yes", "y"])
            )
    return df


def percent_change(new: float, old: float) -> float:
    if old in (None, 0) or pd.isna(old):
        return None
    if new is None or pd.isna(new):
        return None
    return float((new - old) / old)


def build_dataset(
    ts_df: pd.DataFrame,
    detailed_df: pd.DataFrame,
    orga_df: pd.DataFrame,
    limit_days: int = 180,
    top_k_keywords: int = 15,
) -> Dict[str, Any]:
    # Trim time series to last N days
    ts_trim = ts_df.copy()
    if len(ts_trim) > limit_days:
        ts_trim = ts_trim.iloc[-limit_days:].reset_index(drop=True)

    latest_ts = ts_trim.iloc[-1]
    # 7d/30d by position (fallback by available length)
    def by_offset(series: pd.Series, offset: int):
        if len(series) > offset:
            return series.iloc[-offset - 1]
        return None

    latest_pages = latest_ts.get("organic_pages")
    latest_traffic = latest_ts.get("organic_traffic")

    pages_7ago = by_offset(ts_trim["organic_pages"], 7) if "organic_pages" in ts_trim else None
    pages_30ago = by_offset(ts_trim["organic_pages"], 30) if "organic_pages" in ts_trim else None
    traffic_7ago = by_offset(ts_trim["organic_traffic"], 7) if "organic_traffic" in ts_trim else None
    traffic_30ago = by_offset(ts_trim["organic_traffic"], 30) if "organic_traffic" in ts_trim else None

    latest_detailed = detailed_df.iloc[-1] if not detailed_df.empty else None

    # Entities: columns starting with 'Organic entities (traffic): '
    entities: List[Dict[str, Any]] = []
    if latest_detailed is not None:
        for col in detailed_df.columns:
            if isinstance(col, str) and col.lower().startswith("organic entities (traffic):"):
                name = col.split(":", 1)[1].strip()
                val = pd.to_numeric(latest_detailed[col], errors="coerce")
                if pd.notna(val) and val > 0:
                    entities.append({"name": name, "traffic": int(val)})
        entities = sorted(entities, key=lambda x: x["traffic"], reverse=True)[:10]

    # Top keywords by organic traffic
    kw_cols = orga_df.columns
    has_url_inside = "current_url_inside" in kw_cols
    top_kw = (
        orga_df.dropna(subset=["keyword"]) if "keyword" in kw_cols else orga_df.copy()
    )
    if "organic_traffic" in kw_cols:
        top_kw = top_kw.sort_values("organic_traffic", ascending=False)
    elif "volume" in kw_cols:
        top_kw = top_kw.sort_values("volume", ascending=False)
    top_kw = top_kw.head(top_k_keywords)

    intents = [c for c in [
        "navigational",
        "informational",
        "commercial",
        "transactional",
        "branded",
        "local",
    ] if c in kw_cols]

    keywords_top: List[Dict[str, Any]] = []
    for _, r in top_kw.iterrows():
        intent_list = [c for c in intents if bool(r.get(c))]
        keywords_top.append({
            "keyword": r.get("keyword"),
            "volume": _safe_int(r.get("volume")),
            "kd": _safe_float(r.get("kd")),
            "cpc": _safe_float(r.get("cpc")),
            "organic_traffic": _safe_int(r.get("organic_traffic")),
            "current_position": _safe_int(r.get("current_position")),
            "url": r.get("current_url"),
            "url_inside": r.get("current_url_inside") if has_url_inside else None,
            "serp_features": _split_features(r.get("serp_features")),
            "intent": intent_list,
            "updated": r.get("updated"),
        })

    # SERP feature distribution from top keywords
    feature_counts: Dict[str, int] = {}
    for kw in keywords_top:
        for f in kw.get("serp_features") or []:
            feature_counts[f] = feature_counts.get(f, 0) + 1
    feature_counts_sorted = sorted(
        [{"feature": k, "count": v} for k, v in feature_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )

    # Compose dataset
    dataset: Dict[str, Any] = {
        "source": "skyscanner_tips_and_inspiration",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "time_series": [
            {
                "date": d.date.isoformat(),
                "organic_pages": _safe_int(d.get("organic_pages")),
                "organic_traffic": _safe_int(d.get("organic_traffic")),
            }
            for _, d in ts_trim.iterrows()
        ],
        "latest_summary": {
            "date": latest_ts.get("date").date().isoformat(),
            "organic_pages": _safe_int(latest_pages),
            "organic_traffic": _safe_int(latest_traffic),
            "organic_pages_change_7d": percent_change(latest_pages, pages_7ago),
            "organic_pages_change_30d": percent_change(latest_pages, pages_30ago),
            "organic_traffic_change_7d": percent_change(latest_traffic, traffic_7ago),
            "organic_traffic_change_30d": percent_change(latest_traffic, traffic_30ago),
        },
        "positions_and_serp": {},
        "entities_top": entities,
        "keywords_top": keywords_top,
        "serp_feature_counts_top": feature_counts_sorted,
    }

    if latest_detailed is not None:
        dataset["positions_and_serp"] = {
            "date": latest_detailed.get("date").date().isoformat(),
            "positions_top3": _safe_int(latest_detailed.get("positions_top3")),
            "positions_4_10": _safe_int(latest_detailed.get("positions_4_10")),
            "sf_featured_snippet": _safe_int(latest_detailed.get("sf_featured_snippet")),
            "sf_people_also_ask": _safe_int(latest_detailed.get("sf_people_also_ask")),
            "sf_sitelinks": _safe_int(latest_detailed.get("sf_sitelinks")),
            "sf_video_preview": _safe_int(latest_detailed.get("sf_video_preview")),
            "sf_thumbnail": _safe_int(latest_detailed.get("sf_thumbnail")),
        }

    return dataset


def _split_features(v: Any) -> List[str]:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return []
    s = str(v).strip()
    if not s:
        return []
    parts = [p.strip() for p in s.split(",")]
    return [p for p in parts if p]


def _safe_int(v: Any) -> Any:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        return int(round(float(v)))
    except Exception:
        return None


def _safe_float(v: Any) -> Any:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        return float(v)
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description="Build Grok-ready viz dataset from Skyscanner CSVs")
    ap.add_argument("--ts", default="www.skyscanner.com-tips-and-inspiration-perf_2025-08-23_18-58-04.csv", help="Tips & Inspiration time series CSV (Date, Organic pages, Organic traffic)")
    ap.add_argument("--detailed", default="www.skyscanner.com-tips-and-inspiration_perf_2025-08-23_18-54-36.csv", help="Detailed performance CSV with positions and SERP features")
    ap.add_argument("--orga", default="www.skyscanner.com-tips-and-inspiration-orga_2025-08-23_19-00-00.csv", help="Organic keywords CSV (UTF-16 TSV)")
    ap.add_argument("--out", default="data/grok_tips_inspiration_dataset.json", help="Output JSON path")
    ap.add_argument("--days", type=int, default=180, help="Limit time series to last N days")
    ap.add_argument("--top_k", type=int, default=15, help="Number of top keywords to include")
    args = ap.parse_args()

    ts_df = load_time_series(Path(args.ts))
    detailed_df = load_detailed_metrics(Path(args.detailed))
    orga_df = load_keywords_orga(Path(args.orga))

    dataset = build_dataset(ts_df, detailed_df, orga_df, limit_days=args.days, top_k_keywords=args.top_k)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"Wrote dataset to {out_path}")


if __name__ == "__main__":
    main()
