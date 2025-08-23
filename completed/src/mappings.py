"""
Musical mapping utilities for SERP Loop Radio.
Helper functions for timbre, pan, key, and other musical parameter conversions.
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, Union, List
import logging

logger = logging.getLogger(__name__)


class MusicMappings:
    """Helper class for musical parameter mappings and conversions."""
    
    # MIDI General Midi Instrument Map (simplified)
    GM_INSTRUMENTS = {
        0: "Acoustic Grand Piano",
        1: "Bright Acoustic Piano", 
        13: "Xylophone",
        48: "String Ensemble 1",
        81: "Lead 2 (sawtooth)",
        104: "Sitar",
        120: "Reverse Cymbal",
        127: "Applause"
    }
    
    # Musical scales and keys
    SCALES = {
        "major": [0, 2, 4, 5, 7, 9, 11],
        "minor": [0, 2, 3, 5, 7, 8, 10],
        "pentatonic": [0, 2, 4, 7, 9],
        "blues": [0, 3, 5, 6, 7, 10],
        "dorian": [0, 2, 3, 5, 7, 9, 10]
    }
    
    # Note names to MIDI numbers
    NOTE_TO_MIDI = {
        'C': 60, 'C#': 61, 'Db': 61, 'D': 62, 'D#': 63, 'Eb': 63,
        'E': 64, 'F': 65, 'F#': 66, 'Gb': 66, 'G': 67, 'G#': 68,
        'Ab': 68, 'A': 69, 'A#': 70, 'Bb': 70, 'B': 71
    }
    
    def __init__(self, config_path: Path = None):
        """Initialize mappings from config file."""
        self.config = {}
        if config_path and config_path.exists():
            self.load_config(config_path)
    
    def load_config(self, config_path: Path) -> None:
        """Load FATLD configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                self.config = json.load(f)
            logger.info(f"Loaded mapping config from {config_path}")
        except Exception as e:
            logger.error(f"Could not load config: {e}")
            self.config = {}
    
    def map_value_to_range(
        self, 
        value: float, 
        input_range: List[float], 
        output_range: List[float],
        clamp: bool = True
    ) -> float:
        """Map a value from input range to output range."""
        if input_range[1] == input_range[0]:
            return output_range[0]
        
        # Normalize to 0-1
        normalized = (value - input_range[0]) / (input_range[1] - input_range[0])
        
        if clamp:
            normalized = max(0, min(1, normalized))
        
        # Map to output range
        mapped = output_range[0] + normalized * (output_range[1] - output_range[0])
        
        return mapped
    
    def get_pitch_from_rank_delta(self, rank_delta: float) -> int:
        """Convert rank delta to MIDI pitch adjustment."""
        pitch_config = self.config.get("pitch", {})
        input_range = pitch_config.get("range", [-10, 10])
        semitone_multiplier = pitch_config.get("semitone", 1.2)
        
        # Map rank delta to semitone adjustment
        semitones = self.map_value_to_range(
            rank_delta, 
            input_range, 
            [-12, 12]  # +/- one octave
        )
        
        return int(semitones * semitone_multiplier)
    
    def get_velocity_from_share(self, share_pct: float) -> int:
        """Convert share percentage to MIDI velocity."""
        velocity_config = self.config.get("velocity", {})
        input_range = velocity_config.get("range", [0, 1])
        output_range = velocity_config.get("midi", [40, 127])
        
        velocity = self.map_value_to_range(share_pct, input_range, output_range)
        return int(velocity)
    
    def get_instrument_from_engine(self, engine: str) -> int:
        """Get MIDI instrument number from search engine."""
        timbre_config = self.config.get("timbre", {})
        engine_map = timbre_config.get("map", {})
        
        return engine_map.get(engine, 0)  # Default to piano
    
    def get_pan_from_segment(self, segment: str) -> float:
        """Get stereo pan position from geographic segment."""
        pan_config = self.config.get("pan", {})
        segment_map = pan_config.get("map", {})
        
        return segment_map.get(segment, 0)  # Default to center
    
    def get_duration_from_rich_type(self, rich_type: str) -> float:
        """Get note duration from rich snippet type."""
        duration_config = self.config.get("duration", {})
        type_map = duration_config.get("map", {})
        
        return type_map.get(rich_type, 1.0)  # Default to quarter note
    
    def quantize_to_grid(self, time: float, grid_size: float = 0.25) -> float:
        """Quantize timing to musical grid (16th notes by default)."""
        return round(time / grid_size) * grid_size
    
    def get_scale_notes(self, root_note: str = "C", scale: str = "pentatonic") -> List[int]:
        """Get MIDI note numbers for a scale."""
        root_midi = self.NOTE_TO_MIDI.get(root_note, 60)
        scale_intervals = self.SCALES.get(scale, self.SCALES["pentatonic"])
        
        return [root_midi + interval for interval in scale_intervals]
    
    def fit_to_scale(self, midi_note: int, scale_notes: List[int]) -> int:
        """Fit a MIDI note to the closest note in a scale."""
        if not scale_notes:
            return midi_note
        
        # Find closest note in scale
        closest_note = min(scale_notes, key=lambda x: abs(x - midi_note))
        
        # Adjust for octave if needed
        octave_adjustment = (midi_note - closest_note) // 12
        return closest_note + (octave_adjustment * 12)
    
    def create_chord_progression(
        self, 
        root_note: str = "C", 
        progression: List[int] = [1, 5, 6, 4]
    ) -> List[List[int]]:
        """Create a chord progression in a given key."""
        root_midi = self.NOTE_TO_MIDI.get(root_note, 60)
        major_scale = self.SCALES["major"]
        
        chords = []
        for degree in progression:
            # Get the root of the chord (degree - 1 for 0-indexing)
            chord_root = root_midi + major_scale[(degree - 1) % len(major_scale)]
            
            # Create triad (root, third, fifth)
            third = chord_root + major_scale[2]
            fifth = chord_root + major_scale[4]
            
            chords.append([chord_root, third, fifth])
        
        return chords
    
    def get_anomaly_percussion(self) -> int:
        """Get percussion instrument for anomaly events."""
        return 35  # MIDI 35 = Acoustic Bass Drum, 37 = Side Stick


def load_mappings(config_path: Path = None) -> MusicMappings:
    """Factory function to create MusicMappings instance."""
    if config_path is None:
        config_path = Path("config/mapping.json")
    
    return MusicMappings(config_path)


def validate_midi_values(note: int, velocity: int, channel: int = 0) -> tuple:
    """Validate and clamp MIDI values to legal ranges."""
    note = max(0, min(127, int(note)))
    velocity = max(0, min(127, int(velocity)))
    channel = max(0, min(15, int(channel)))
    
    return note, velocity, channel


def beats_to_ticks(beats: float, ticks_per_beat: int = 480) -> int:
    """Convert musical beats to MIDI ticks."""
    return int(beats * ticks_per_beat)


def calculate_tempo_factor(source_bpm: int, target_bpm: int) -> float:
    """Calculate tempo scaling factor."""
    return target_bpm / source_bpm


if __name__ == "__main__":
    # Test mappings
    mappings = load_mappings()
    
    # Test pitch mapping
    print("Rank delta -5 -> pitch adjustment:", mappings.get_pitch_from_rank_delta(-5))
    
    # Test scale generation
    c_pentatonic = mappings.get_scale_notes("C", "pentatonic")
    print("C Pentatonic scale:", c_pentatonic)
    
    # Test chord progression
    progression = mappings.create_chord_progression("C", [1, 5, 6, 4])
    print("I-V-vi-IV progression in C:", progression) 