"""Runtime helpers for FastAI motif label prediction."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from fastai.learner import load_learner
except ImportError:  # pragma: no cover - handled at runtime
    load_learner = None  # type: ignore


FEATURE_NAMES = [
    "note_count",
    "avg_velocity",
    "note_density",
    "duration",
    "pitch_range",
    "lowest_pitch",
    "highest_pitch",
    "pitch_span",
]


def _default_model_path() -> Path:
    env_path = os.getenv("VIBENET_FASTAI_MODEL")
    if env_path:
        return Path(env_path)
    return Path("models/vibenet_fastai_motif.pkl")


@lru_cache(maxsize=1)
def _load_model_cached(path: Path) -> Optional[Any]:
    if load_learner is None:
        logger.debug("fastai not installed; skipping motif label predictor")
        return None
    if not path.exists():
        logger.debug("FastAI model path not found: %s", path)
        return None
    try:
        logger.info("Loading FastAI motif model from %s", path)
        return load_learner(path)
    except Exception as exc:  # pragma: no cover - runtime failure
        logger.warning("Failed to load FastAI learner: %s", exc)
        return None


def _motif_to_features(motif: Dict[str, Any]) -> Optional[Dict[str, float]]:
    meta = motif.get("metadata") or {}
    try:
        lowest = float(meta.get("lowest_pitch", 0) or 0)
        highest = float(meta.get("highest_pitch", 0) or 0)
        return {
            "note_count": float(meta.get("note_count", 0) or 0),
            "avg_velocity": float(meta.get("avg_velocity", 0) or 0),
            "note_density": float(meta.get("note_density", 0) or 0),
            "duration": float(meta.get("duration", 0) or 0),
            "pitch_range": float(meta.get("pitch_range", 0) or (highest - lowest)),
            "lowest_pitch": lowest,
            "highest_pitch": highest,
            "pitch_span": highest - lowest,
        }
    except Exception as exc:  # pragma: no cover - guard errors
        logger.debug("Unable to convert motif metadata to features: %s", exc)
        return None


def predict_motif_label(motif: Dict[str, Any], model_path: Optional[Path] = None) -> Optional[str]:
    """Predict a motif label using the FastAI learner (if available)."""

    model_path = model_path or _default_model_path()
    learner = _load_model_cached(model_path)
    if learner is None:
        return None

    feats = _motif_to_features(motif)
    if not feats:
        return None

    df = pd.DataFrame([feats])
    try:
        dl = learner.dls.test_dl(df, reorder=False)
        preds, _ = learner.get_preds(dl=dl)
        if preds is None or len(preds) == 0:
            return None
        idx = int(preds.argmax(dim=1)[0].item())
        vocab = getattr(learner.dls, "vocab", None)
        if isinstance(vocab, list) and 0 <= idx < len(vocab):
            return str(vocab[idx])
    except Exception as exc:  # pragma: no cover
        logger.debug("FastAI prediction failed: %s", exc)
    return None

