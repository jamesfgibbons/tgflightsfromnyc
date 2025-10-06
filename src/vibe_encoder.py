"""
Rule-first Vibe Encoder and lightweight feature extraction.

Maps numeric time-series into a continuous VibeVector suitable for musical binding.
The mapping is intentionally simple and deterministic; a learned head can be added later.
"""
from __future__ import annotations
from typing import Dict, List, Tuple
import math

from .vibe_ir import VibeVector


def _normalize(vals: List[float]) -> List[float]:
    if not vals:
        return []
    vmin = min(vals)
    vmax = max(vals)
    if math.isclose(vmax, vmin):
        return [0.5 for _ in vals]
    return [(float(v) - vmin) / (vmax - vmin) for v in vals]


def _ema(vals: List[float], alpha: float = 0.3) -> List[float]:
    if not vals:
        return []
    out = [vals[0]]
    for v in vals[1:]:
        out.append(alpha * v + (1.0 - alpha) * out[-1])
    return out


def _rolling_std(vals: List[float], w: int = 8) -> List[float]:
    out: List[float] = []
    for i in range(len(vals)):
        s = max(0, i - w + 1)
        win = vals[s : i + 1]
        if not win:
            out.append(0.0)
            continue
        mean = sum(win) / len(win)
        var = sum((x - mean) ** 2 for x in win) / max(1, len(win) - 1)
        out.append(math.sqrt(max(0.0, var)))
    return out


def _zscore(x: float, mean: float, std: float) -> float:
    if std <= 1e-8:
        return 0.0
    return (x - mean) / std


def extract_features(series: List[float]) -> Dict[str, float]:
    """Compute a minimal feature set over the series (normalized)."""
    xs = _normalize([float(v) for v in series])
    if not xs:
        return {
            "level": 0.5,
            "delta": 0.0,
            "momentum": 0.0,
            "volatility": 0.0,
            "anomaly": 0.0,
        }

    # Level & delta
    level = xs[-1]
    delta = xs[-1] - xs[0]

    # Momentum (EMA slope)
    ema = _ema(xs, alpha=0.3)
    momentum = ema[-1] - ema[max(0, len(ema) - 5)]  # ~ last few steps

    # Volatility (rolling std)
    stds = _rolling_std(xs, w=max(4, len(xs) // 8))
    volatility = stds[-1]

    # Anomaly (latest z vs window)
    win = xs[-16:] if len(xs) >= 16 else xs
    mean = sum(win) / len(win)
    std = (sum((x - mean) ** 2 for x in win) / max(1, len(win) - 1)) ** 0.5
    anomaly = abs(_zscore(xs[-1], mean, std))

    return {
        "level": float(level),
        "delta": float(delta),
        "momentum": float(momentum),
        "volatility": float(volatility),
        "anomaly": float(anomaly),
    }


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def embed_vibe(series: List[float], palette: str | None = None) -> VibeVector:
    """Rule mapping from extracted features to VibeVector.

    Intuition:
    - Momentum up & low volatility → happier + more energetic, less tension
    - Choppy periods → higher tension + syncopation + harmonic complexity
    - Anomaly spike → short-term arousal/tension bump
    """
    feats = extract_features(series)
    level = feats["level"]
    momentum = feats["momentum"]
    vol = feats["volatility"]
    delta = feats["delta"]
    anom = feats["anomaly"]

    # Base axes
    valence = clamp01(0.5 + 0.35 * momentum - 0.15 * vol + 0.1 * delta)
    arousal = clamp01(0.5 + 0.4 * abs(momentum) + 0.2 * vol + 0.1 * anom)
    tension = clamp01(0.35 + 0.5 * vol + 0.15 * anom - 0.2 * momentum)

    # Timbre & density
    brightness = clamp01(0.4 + 0.4 * level)
    warmth = clamp01(0.5 + 0.3 * (1.0 - vol))
    density = clamp01(0.3 + 0.6 * (abs(momentum) + vol) / 2.0)
    syncopation = clamp01(0.2 + 0.6 * vol)
    harm_complexity = clamp01(0.2 + 0.6 * vol + 0.15 * max(0.0, -momentum))

    # Meter: prefer straight_4; if high syncopation, occasionally pick 12_8
    meter = "12_8" if syncopation > 0.7 else "straight_4"

    return VibeVector(
        valence=valence,
        arousal=arousal,
        tension=tension,
        brightness=brightness,
        warmth=warmth,
        density=density,
        syncopation=syncopation,
        harm_complexity=harm_complexity,
        palette=palette or "synthwave_midnight",
        meter=meter,  # type: ignore
    )


def apply_context_nudge(v: VibeVector, context: Dict[str, float] | None) -> VibeVector:
    """Nudge VibeVector using curated context scores.

    Expected keys: deal_score, novelty_score, brand_pref_score, region_pref_score,
    anomaly_score, airport_disruption_score, booking_now_score (0..1 where applicable).
    """
    if not context:
        return v

    def clamp(x: float) -> float:
        return max(0.0, min(1.0, x))

    val = v.model_copy(deep=True)
    deal = float(context.get("deal_score", 0.0) or 0.0)
    nov = float(context.get("novelty_score", 0.0) or 0.0)
    brand = float(context.get("brand_pref_score", 0.0) or 0.0)
    region = float(context.get("region_pref_score", 0.0) or 0.0)
    anom = float(context.get("anomaly_score", 0.0) or 0.0)
    air = float(context.get("airport_disruption_score", 0.0) or 0.0)
    booknow = float(context.get("booking_now_score", 0.0) or 0.0)

    # Deals: happier, slightly less tense
    val.valence = clamp(val.valence + 0.25 * (deal - 0.5))
    val.tension = clamp(val.tension - 0.15 * (deal - 0.5))

    # Novelty: more aroused, more syncopation
    val.arousal = clamp(val.arousal + 0.3 * (nov - 0.5))
    val.syncopation = clamp(val.syncopation + 0.25 * (nov - 0.5))

    # Airport disruption/anomaly: increase tension/harm_complexity; add urgency
    val.tension = clamp(val.tension + 0.4 * anom + 0.4 * air)
    val.harm_complexity = clamp(val.harm_complexity + 0.3 * anom + 0.2 * air)
    val.arousal = clamp(val.arousal + 0.2 * (anom + air))

    # Booking now: urgency → arousal up
    val.arousal = clamp(val.arousal + 0.3 * (booknow - 0.5))

    # Regional preference: timbre warmth/brightness slight shifts
    val.warmth = clamp(val.warmth + 0.15 * (region - 0.5))
    val.brightness = clamp(val.brightness + 0.1 * (brand - 0.5))

    return val
