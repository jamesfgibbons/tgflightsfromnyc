"""
Harmony Designer: choose key/mode and build bar-wise chord plans.

Adds an epic loop designer that can blend an anthemic intro block with a
high‑energy drop block (e.g., arena rock riff) to support "about to drop deals"
moments without using any copyrighted melody.
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
import os
import yaml

from .vibe_ir import VibeVector, HarmonyPlan, HarmonyBar


def choose_key_mode(v: VibeVector) -> tuple[str, str]:
    """Pick a musical key/mode from the vibe vector using simple thresholds."""
    # Mode selection
    if v.tension > 0.6:
        mode = "phrygian"
    elif v.valence > 0.55:
        mode = "ionian"
    else:
        mode = "dorian"

    # Key center nudge by brightness (brighter → sharper keys)
    keys = ["F", "C", "G", "D", "A", "E", "B"]
    idx = int(round(v.brightness * (len(keys) - 1)))
    key = keys[idx]
    return key, mode


def build_progression(v: VibeVector, bars: int = 16) -> List[str]:
    """Return a chord symbol per bar for a compact set of palettes.

    - ionian uplift: I–V–vi–IV
    - dorian loop: i–VII–VI–VII
    - phrygian suspense: i–bII–i–bII
    """
    if v.harm_complexity > 0.6:
        ext = "7"  # tastefully add 7ths on complex vibes
    else:
        ext = ""

    if v.valence > 0.55 and v.tension < 0.6:
        block = [f"I{ext}", f"V{ext}", f"vi{ext}", f"IV{ext}"]
    elif v.tension > 0.6:
        block = [f"i{ext}", "bII", f"i{ext}", "bII"]
    else:
        block = [f"i{ext}", "VII", "VI", "VII"]

    prog = [block[i % 4] for i in range(bars)]
    # Borrowed iv at turns for ionian cases
    if "I" in block[0]:
        for i in range(7, bars, 8):
            prog[i] = "iv"  # borrowing
    return prog


def design_harmony(v: VibeVector, bars: int = 16) -> HarmonyPlan:
    key, mode = choose_key_mode(v)
    chords = build_progression(v, bars)
    plan = HarmonyPlan(key=key, mode=mode, bars=[])
    for i, ch in enumerate(chords, start=1):
        hb = HarmonyBar(bar=i, chord=ch)
        if ch == "iv":
            hb.borrowed = "iv"
            hb.turn = True
        plan.bars.append(hb)
    return plan


# --- Epic Harmony Loop (Palette‑aware) ---

def _load_palettes() -> List[Dict[str, Any]]:
    """Load palettes from config file (same format used by VibeNet API)."""
    path = os.getenv("VIBE_PALETTES_PATH", "config/vibe_palettes.yaml")
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f) or []
    except FileNotFoundError:
        return []


def _find_palette(slug: str) -> Optional[Dict[str, Any]]:
    for p in _load_palettes():
        if str(p.get("slug")) == slug:
            return p
    return None


def design_epic_harmony_from_palette(
    palette_slug: str,
    bars: int = 16,
    drop_every: int = 8,
    intro_block_key: str = "anthemic_lift",
    drop_block_key: str = "power_riff_mix",
) -> HarmonyPlan:
    """Design a hybrid intro→drop progression using palette chord blocks.

    - Uses `intro_block_key` if present, else falls back to a generic pop block.
    - Uses `drop_block_key` if present, else falls back to a simple V–IV–I–V loop.
    - Alternates blocks such that the last 4 bars of each `drop_every` segment use the drop block.
    """
    pal = _find_palette(palette_slug) or {}
    blocks = (pal.get("chord_blocks_json") or {}) if isinstance(pal, dict) else {}

    intro = blocks.get(intro_block_key) or ["I", "V", "vi", "IV"]
    drop = blocks.get(drop_block_key) or ["V", "IV", "I", "V"]

    plan = HarmonyPlan(key=str(pal.get("key", "C")), mode=str(pal.get("mode_preference", "ionian")), bars=[])

    for i in range(bars):
        # Last 4 bars of each segment become the drop
        seg_pos = i % max(1, drop_every)
        use_drop = seg_pos >= max(0, drop_every - 4)
        block = drop if use_drop else intro
        chord = block[i % len(block)]
        hb = HarmonyBar(bar=i + 1, chord=chord)
        plan.bars.append(hb)

    return plan


def design_epic_harmony_blend(
    intro_palette: str,
    drop_palette: str,
    bars: int = 16,
    drop_every: int = 8,
    intro_block_key: str = "anthemic_lift",
    drop_block_key: str = "chase_loop",
) -> HarmonyPlan:
    """Blend two palettes (intro→drop). Useful for segues between themes.

    Example: intro_palette="circle_of_life_travel", drop_palette="new_wave_hunt".
    """
    pal_intro = _find_palette(intro_palette) or {}
    pal_drop = _find_palette(drop_palette) or {}

    blocks_intro = (pal_intro.get("chord_blocks_json") or {}) if isinstance(pal_intro, dict) else {}
    blocks_drop = (pal_drop.get("chord_blocks_json") or {}) if isinstance(pal_drop, dict) else {}

    intro = blocks_intro.get(intro_block_key) or ["I", "V", "vi", "IV"]
    drop = blocks_drop.get(drop_block_key) or ["i", "VI", "III", "VII"]

    key = str(pal_intro.get("key", "C"))
    mode = str(pal_intro.get("mode_preference", "ionian"))
    plan = HarmonyPlan(key=key, mode=mode, bars=[])

    for i in range(bars):
        seg_pos = i % max(1, drop_every)
        use_drop = seg_pos >= max(0, drop_every - 4)
        block = drop if use_drop else intro
        chord = block[i % len(block)]
        plan.bars.append(HarmonyBar(bar=i + 1, chord=chord))

    return plan
