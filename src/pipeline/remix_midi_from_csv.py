"""
Remix a local MIDI file using flight price metrics as a vibe pattern.

Usage:
  python -m src.pipeline.remix_midi_from_csv \
    --input-midi JMX-2025-Oct-05-1.11.6.pm.mid \
    --csv seed_flight_price_data.csv \
    --origin JFK \
    --out-dir data/remixes \
    --bars 16

This script computes a simple numeric pattern from flight price data, derives
sonification controls + motif selection, and applies them to the provided MIDI
as a base template. Outputs a remixed MIDI file under the out directory.
"""
from __future__ import annotations

import argparse
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import sys

# Ensure we can import from the repository's 'completed' directory
sys.path.append(str(Path(__file__).parent.parent.parent / "completed"))

# Use the completed/ domain logic for controls/motifs and MIDI writing
from map_to_controls import map_metrics_to_controls, Controls
from motif_selector import select_motifs_for_controls
from transform_midi import create_sonified_midi


def _normalize(vals: List[float]) -> List[float]:
    if not vals:
        return []
    vmin = min(vals)
    vmax = max(vals)
    if math.isclose(vmax, vmin):
        return [0.5 for _ in vals]
    return [(v - vmin) / (vmax - vmin) for v in vals]


def _segments_to_bands(norm: List[float], segment_count: int) -> List[Dict[str, Any]]:
    if segment_count <= 0:
        segment_count = 8
    n = len(norm)
    if n == 0:
        return [
            {"t0": 0.0, "t1": 6.4, "label": "positive", "score": 0.6},
            {"t0": 6.4, "t1": 12.8, "label": "neutral", "score": 0.5},
        ]
    size = max(1, n // segment_count)
    bands: List[Dict[str, Any]] = []
    t = 0.0
    for i in range(segment_count):
        start = i * size
        end = n if i == segment_count - 1 else min(n, (i + 1) * size)
        if start >= end:
            mean = sum(norm) / len(norm)
        else:
            mean = sum(norm[start:end]) / (end - start)
        score = max(-1.0, min(1.0, (mean - 0.5) * 2.0))
        label = "positive" if score > 0.15 else ("negative" if score < -0.15 else "neutral")
        bands.append({"t0": t, "t1": t + 3.2, "label": label, "score": round(score, 3)})
        t += 3.2
    return bands


def _derive_metrics_from_flights(df: pd.DataFrame) -> Dict[str, float]:
    """
    Produce a minimal, normalized SERP-like metric dict from flight rows.

    - ctr: inverse of normalized median price
    - impressions: dispersion of median price (range proxy)
    - position: inverse of normalized best_booking_window
    - clicks: normalized novelty_score (1..10 -> 0..1)
    """
    # Median price across rows as a simple scalar
    median_price = ((df["estimated_price_min"].astype(float) + df["estimated_price_max"].astype(float)) / 2.0).tolist()
    norm_median = _normalize(median_price)
    avg_norm_price = sum(norm_median) / max(1, len(norm_median)) if norm_median else 0.5

    # Price dispersion proxy for impressions
    if median_price:
        pr_min, pr_max = min(median_price), max(median_price)
        impressions = 0.0 if pr_max == pr_min else min(1.0, (pr_max - pr_min) / max(1.0, pr_max))
    else:
        impressions = 0.5

    # Position from booking window (lower window -> better "position")
    if "best_booking_window" in df.columns and len(df["best_booking_window"]) > 0:
        wnd = df["best_booking_window"].astype(float).tolist()
        wnd_norm = _normalize(wnd)
        avg_wnd = sum(wnd_norm) / max(1, len(wnd_norm))
        position = 1.0 - avg_wnd
    else:
        position = 0.5

    # Clicks from novelty score (1..10)
    if "novelty_score" in df.columns and len(df["novelty_score"]) > 0:
        clicks = float(pd.to_numeric(df["novelty_score"], errors="coerce").fillna(5).mean() / 10.0)
    else:
        clicks = 0.5

    # CTR as inverse of normalized average price
    ctr = 1.0 - avg_norm_price

    # Clamp to [0,1]
    def _clamp01(x: float) -> float:
        return max(0.0, min(1.0, float(x)))

    return {
        "ctr": _clamp01(ctr),
        "impressions": _clamp01(impressions),
        "position": _clamp01(position),
        "clicks": _clamp01(clicks),
    }


def remix_midi(
    input_midi_path: str,
    csv_path: str,
    origin: Optional[str],
    out_dir: str,
    bars: int,
    vibe_slug: Optional[str] = None,
    tempo_hint: Optional[int] = None,
    tenant: str = "poc_local",
) -> Tuple[str, Dict[str, Any]]:
    # Load rows
    df = pd.read_csv(csv_path)
    if origin and "origin" in df.columns:
        df = df[df["origin"] == origin] if origin else df
    if df.empty:
        raise ValueError("No rows available after filtering")

    # Build primary numeric series from median prices for bands/tempo
    series = ((df["estimated_price_min"].astype(float) + df["estimated_price_max"].astype(float)) / 2.0).tolist()
    norm = _normalize(series)

    # Segment into bands
    segment_count = min(10, max(3, len(norm) // 8))
    bands = _segments_to_bands(norm, segment_count)

    # Tempo heuristic from volatility if not provided
    if tempo_hint is None:
        diffs = [abs(a - b) for a, b in zip(norm[1:], norm[:-1])]
        energy = sum(diffs) / max(1, len(diffs)) if diffs else 0.2
        tempo = int(104 + min(1.0, energy * 2.0) * (120 - 104))
    else:
        tempo = tempo_hint

    # Controls from derived SERP-like metrics
    metrics = _derive_metrics_from_flights(df)
    controls: Controls = map_metrics_to_controls(metrics, tenant, mode="serp")
    # Override tempo with our heuristic for a tighter mapping
    controls = Controls(
        bpm=tempo,
        transpose=controls.transpose,
        velocity=controls.velocity,
        cc74_filter=controls.cc74_filter,
        reverb_send=controls.reverb_send,
    )

    # Motif selection
    motifs = select_motifs_for_controls(controls, tenant, num_motifs=4)

    # Output path
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    stem = Path(input_midi_path).stem
    out_path = str(Path(out_dir) / f"{stem}.remix.{ts}.mid")

    # Create MIDI using the input as base_template
    ok = create_sonified_midi(
        controls=controls,
        motifs=motifs,
        output_path=out_path,
        tenant_id=tenant,
        base_template=input_midi_path,
    )

    if not ok:
        raise RuntimeError("Failed to create remixed MIDI")

    info = {
        "output_midi": out_path,
        "tempo": tempo,
        "bands": bands,
        "metrics": metrics,
    }
    return out_path, info


def main() -> None:
    p = argparse.ArgumentParser(description="Remix a local MIDI using flight price metrics")
    p.add_argument("--input-midi", required=True, help="Path to local MIDI file to remix")
    p.add_argument("--csv", default="seed_flight_price_data.csv", help="CSV with flight price rows")
    p.add_argument("--origin", default=None, help="Optional origin filter (e.g., JFK)")
    p.add_argument("--out-dir", default="data/remixes", help="Directory for remixed outputs")
    p.add_argument("--bars", type=int, default=16, help="Target bar count (for band timing only)")
    p.add_argument("--tempo", type=int, default=None, help="Optional tempo override (BPM)")
    args = p.parse_args()

    out_path, info = remix_midi(
        input_midi_path=args.input_midi,
        csv_path=args.csv,
        origin=args.origin,
        out_dir=args.out_dir,
        bars=args.bars,
        tempo_hint=args.tempo,
    )

    print(f"Remix complete: {out_path}")
    print(f"Tempo: {info['tempo']} BPM, Bands: {len(info['bands'])}")


if __name__ == "__main__":
    main()
