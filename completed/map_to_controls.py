"""
Map SERP metrics to MIDI control parameters for sonification.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class Controls:
    """MIDI control parameters derived from SERP metrics."""
    bpm: int  # Tempo (40-200)
    transpose: int  # Pitch shift in semitones (-24 to +24)
    velocity: int  # Note velocity (1-127)
    cc74_filter: int  # Filter cutoff CC74 (0-127)
    reverb_send: int  # Reverb send level (0-127)
    
    def __post_init__(self) -> None:
        """Validate all parameters are within MIDI range."""
        self._validate_range("bpm", self.bpm, 40, 200)
        self._validate_range("transpose", self.transpose, -24, 24)
        self._validate_range("velocity", self.velocity, 1, 127)
        self._validate_range("cc74_filter", self.cc74_filter, 0, 127)
        self._validate_range("reverb_send", self.reverb_send, 0, 127)
    
    def _validate_range(self, param: str, value: int, min_val: int, max_val: int) -> None:
        """Validate parameter is within acceptable range."""
        if not min_val <= value <= max_val:
            raise ValueError(f"{param} must be between {min_val} and {max_val}, got {value}")


def map_metrics_to_controls(
    metrics: Dict[str, Any],
    tenant_id: str,
    mode: str = "serp"
) -> Controls:
    """
    Map normalized SERP metrics to MIDI control parameters.
    
    Args:
        metrics: Dictionary of normalized metrics (0.0-1.0 range)
        tenant_id: Tenant identifier for logging
        mode: Processing mode ("serp" or "gsc")
    
    Returns:
        Controls dataclass with validated MIDI parameters
    """
    logger.info(f"Mapping metrics to controls for tenant {tenant_id}, mode {mode}")
    
    # Extract normalized metrics with fallbacks
    click_through_rate = float(metrics.get("ctr", 0.5))
    impressions = float(metrics.get("impressions", 0.5))
    position = float(metrics.get("position", 0.5))
    clicks = float(metrics.get("clicks", 0.5))
    
    # Map CTR to tempo (higher CTR = faster tempo)
    bpm = int(40 + (click_through_rate * 160))
    
    # Map average position to transpose (higher position = lower pitch)
    # Invert position so lower position numbers (better ranking) = higher pitch
    transpose = int(-12 + ((1.0 - position) * 24))
    
    # Map impressions to velocity (more impressions = louder)
    velocity = max(1, int(20 + (impressions * 107)))
    
    # Map clicks to filter cutoff (more clicks = brighter sound)
    cc74_filter = int(clicks * 127)
    
    # Map combined engagement metric to reverb
    engagement = (click_through_rate + (clicks * 0.5)) / 1.5
    reverb_send = int(engagement * 127)
    
    controls = Controls(
        bpm=bpm,
        transpose=transpose,
        velocity=velocity,
        cc74_filter=cc74_filter,
        reverb_send=reverb_send
    )
    
    logger.info(f"Generated controls for tenant {tenant_id}: "
               f"BPM={bpm}, transpose={transpose}, velocity={velocity}, "
               f"filter={cc74_filter}, reverb={reverb_send}")
    
    return controls


def apply_mode_adjustments(controls: Controls, mode: str) -> Controls:
    """
    Apply mode-specific adjustments to controls.
    
    Args:
        controls: Base controls to adjust
        mode: Processing mode ("serp" or "gsc")
    
    Returns:
        Adjusted controls
    """
    if mode == "gsc":
        # GSC mode: More conservative tempo, emphasis on filter
        adjusted_bpm = max(60, min(140, controls.bpm - 20))
        adjusted_filter = min(127, controls.cc74_filter + 20)
        
        return Controls(
            bpm=adjusted_bpm,
            transpose=controls.transpose,
            velocity=controls.velocity,
            cc74_filter=adjusted_filter,
            reverb_send=controls.reverb_send
        )
    
    return controls


def get_fallback_controls(tenant_id: str) -> Controls:
    """
    Get safe fallback controls when metrics are unavailable.
    
    Args:
        tenant_id: Tenant identifier for logging
    
    Returns:
        Default Controls with middle-range values
    """
    logger.warning(f"Using fallback controls for tenant {tenant_id}")
    
    return Controls(
        bpm=120,
        transpose=0,
        velocity=64,
        cc74_filter=64,
        reverb_send=32
    )