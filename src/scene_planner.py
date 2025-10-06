"""Scene planner: map momentum and booking windows into musical sections.

Scenes: verse | pre | chorus | drop
This module returns a bar-wise schedule for downstream arrangement.
"""
from __future__ import annotations
from typing import List, Dict, Any


def build_scene_schedule(
    momentum_data: Dict[str, Any] | None,
    total_bars: int = 16,
) -> List[str]:
    """Return a bar-wise list of scene labels.

    Heuristics:
    - If any positive momentum exists → last half of bars are chorus.
    - Otherwise all verse.
    - Reserve a 4-bar pre just before chorus when possible.
    """
    if total_bars <= 0:
        total_bars = 16
    schedule = ["verse"] * total_bars

    has_positive = False
    if momentum_data and isinstance(momentum_data.get("momentum"), list):
        for sec in momentum_data["momentum"]:
            lbl = str(sec.get("label") or "").upper()
            if "POS" in lbl:
                has_positive = True
                break

    if has_positive:
        half = total_bars // 2
        # Pre-chorus for 4 bars before chorus if space allows
        pre_len = 4 if half >= 4 else max(0, half - 1)
        for i in range(half - pre_len, half):
            if 0 <= i < total_bars:
                schedule[i] = "pre"
        for i in range(half, total_bars):
            schedule[i] = "chorus"

    return schedule

