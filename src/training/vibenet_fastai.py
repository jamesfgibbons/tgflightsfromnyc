"""FastAI integration for VibeNet motif label training.

This module consumes the curated motif catalog (``completed/motifs_catalog.json``)
and trains a lightweight classifier that maps motif metadata → momentum labels.

Usage (after cloning fastai locally or installing the ``fastai`` package)::

    python -m src.training.vibenet_fastai --epochs 5 --bs 64 \
        --catalog completed/motifs_catalog.json \
        --export models/vibenet_fastai_motif.pkl

The exported model can later be loaded with ``fastai.load_learner`` to provide
fast heuristics when selecting motifs for new VibeNet jobs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from pickle import HIGHEST_PROTOCOL
from typing import Iterable

import pandas as pd


# Ensure completed/ modules are importable when running as script
completed_root = Path(__file__).parent.parent.parent / "completed"
if completed_root.exists() and str(completed_root) not in sys.path:
    sys.path.insert(0, str(completed_root))


try:
    from fastai.tabular.all import (
        Categorify,
        FillMissing,
        Normalize,
        RandomSplitter,
        TabularPandas,
        accuracy,
        tabular_learner,
    )
except ImportError:
    repo_root = Path(__file__).resolve().parents[2]
    fastai_repo = repo_root / "fastai"
    if fastai_repo.exists() and str(fastai_repo) not in sys.path:
        sys.path.insert(0, str(fastai_repo))
    try:
        from fastai.tabular.all import (  # type: ignore
            Categorify,
            FillMissing,
            Normalize,
            RandomSplitter,
            TabularPandas,
            accuracy,
            tabular_learner,
        )
    except ImportError as exc:  # pragma: no cover - guard for missing dependency
        raise ImportError(
            "fastai is required for training. Install via pip or provide a local clone." 
        ) from exc


def load_motif_dataframe(catalog_path: Path) -> pd.DataFrame:
    """Load labeled motifs into a flat DataFrame suitable for FastAI."""

    with catalog_path.open("r") as fh:
        data = json.load(fh)

    rows = []
    for motif in data.get("motifs", []):
        label = motif.get("label") or "UNLABELED"
        if label == "UNLABELED":
            continue  # skip unlabeled rows for supervised training
        meta = motif.get("metadata", {})
        rows.append(
            {
                "id": motif.get("id"),
                "label": label,
                "note_count": meta.get("note_count"),
                "avg_velocity": meta.get("avg_velocity"),
                "note_density": meta.get("note_density"),
                "duration": meta.get("duration"),
                "pitch_range": meta.get("pitch_range"),
                "lowest_pitch": meta.get("lowest_pitch"),
                "highest_pitch": meta.get("highest_pitch"),
                "pitch_span": (meta.get("highest_pitch", 0) or 0)
                - (meta.get("lowest_pitch", 0) or 0),
            }
        )

    if not rows:
        raise ValueError(
            f"No labeled motifs found in {catalog_path}. Annotate catalog before training."
        )

    df = pd.DataFrame(rows)
    df = df.dropna()
    return df


def build_dataloaders(df: pd.DataFrame, valid_pct: float, seed: int, bs: int):
    """Create FastAI Tabular dataloaders for training."""

    cont_names = [
        "note_count",
        "avg_velocity",
        "note_density",
        "duration",
        "pitch_range",
        "lowest_pitch",
        "highest_pitch",
        "pitch_span",
    ]
    cat_names: Iterable[str] = []
    splits = RandomSplitter(valid_pct=valid_pct, seed=seed)(list(range(len(df))))

    to = TabularPandas(
        df,
        procs=[Categorify, FillMissing, Normalize],
        cat_names=list(cat_names),
        cont_names=cont_names,
        y_names="label",
        splits=splits,
    )
    return to.dataloaders(bs=bs)


def train_motif_classifier(
    catalog_path: Path,
    epochs: int = 5,
    bs: int = 64,
    valid_pct: float = 0.2,
    seed: int = 42,
    export_path: Path | None = None,
):
    """Train a FastAI tabular classifier on motif metadata."""

    df = load_motif_dataframe(catalog_path)
    dls = build_dataloaders(df, valid_pct=valid_pct, seed=seed, bs=bs)
    learn = tabular_learner(dls, metrics=accuracy)
    learn.fit(epochs)

    if export_path:
        export_path.parent.mkdir(parents=True, exist_ok=True)
        learn.export(export_path, pickle_protocol=HIGHEST_PROTOCOL)
    return learn


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a FastAI motif label classifier")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("completed/motifs_catalog.json"),
        help="Path to motifs_catalog.json",
    )
    parser.add_argument("--epochs", type=int, default=5, help="Number of training epochs")
    parser.add_argument("--bs", type=int, default=64, help="Batch size")
    parser.add_argument(
        "--valid-pct", type=float, default=0.2, help="Validation split percentage"
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for dataset splitter"
    )
    parser.add_argument(
        "--export",
        type=Path,
        default=Path("models/vibenet_fastai_motif.pkl"),
        help="Where to export the trained learner",
    )

    args = parser.parse_args()
    train_motif_classifier(
        catalog_path=args.catalog,
        epochs=args.epochs,
        bs=args.bs,
        valid_pct=args.valid_pct,
        seed=args.seed,
        export_path=args.export,
    )


if __name__ == "__main__":
    main()
