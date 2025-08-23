"""
Nostalgia / emotive mapping utilities.
"""
from typing import Dict, Tuple

def brand_to_sound_pack(brand: str) -> str:
    b = (brand or "").lower()
    if any(x in b for x in ["spirit","frontier","allegiant","budget"]):
        return "8-Bit"         # playful, frugal vibe
    if any(x in b for x in ["las vegas","vegas","casino","resort","nightlife"]):
        return "Synthwave"     # neon, 80s shimmer
    if any(x in b for x in ["delta","american","united","legacy","flagship","expedia"]):
        return "Arena Rock"    # big, confident
    return "Synthwave"

def routing_to_energy(strategy: str) -> Tuple[int,int]:
    # returns (tempo_base, bars)
    if strategy == "direct":
        return (112, 28)
    if strategy == "connecting":
        return (120, 32)
    if strategy == "hidden-city":
        return (128, 36)
    if strategy == "multi-city":
        return (124, 36)
    return (120, 32)