"""
Sound pack definitions with General MIDI instrument mappings.
Each pack defines a complete sonic palette for SERP Radio sonification.
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class InstrumentConfig:
    """Configuration for a single instrument."""
    program: int  # General MIDI program number (0-127)
    volume: float = 0.8  # Relative volume (0.0-1.0)
    pan: float = 0.5  # Pan position (0.0=left, 1.0=right)
    reverb: float = 0.2  # Reverb send (0.0-1.0)


@dataclass 
class SoundPack:
    """Complete sound pack configuration."""
    name: str
    description: str
    tempo_range: tuple[int, int]  # (min_bpm, max_bpm)
    instruments: Dict[str, InstrumentConfig]
    
    def get_instrument(self, role: str) -> InstrumentConfig:
        """Get instrument config for a role, with fallback."""
        return self.instruments.get(role, self.instruments.get('lead', InstrumentConfig(0)))


# Arena Rock: Big, powerful, stadium sound
ARENA_ROCK = SoundPack(
    name="Arena Rock",
    description="Brass stabs, power chords, big tom fills - stadium anthem energy",
    tempo_range=(110, 130),
    instruments={
        # Melodic instruments
        'lead': InstrumentConfig(30, volume=0.9, pan=0.6),  # Overdriven Guitar
        'bass': InstrumentConfig(33, volume=0.8, pan=0.4),  # Electric Bass (finger)
        'pad': InstrumentConfig(51, volume=0.6, pan=0.5, reverb=0.4),  # String pad
        'pluck': InstrumentConfig(25, volume=0.7, pan=0.7),  # Steel Guitar
        'arp': InstrumentConfig(12, volume=0.6, pan=0.3),   # Vibraphone
        
        # Fanfare and accents
        'fanfare': InstrumentConfig(56, volume=0.9, pan=0.5),  # Trumpet (brass stab)
        'stab': InstrumentConfig(61, volume=0.8, pan=0.5),     # Brass Section
        
        # Drums (channel 9/10 - GM drum kit)
        'kick': InstrumentConfig(0, volume=0.9, pan=0.5),      # Acoustic Bass Drum
        'snare': InstrumentConfig(0, volume=0.8, pan=0.5),     # Acoustic Snare
        'hihat': InstrumentConfig(0, volume=0.6, pan=0.3),     # Closed Hi-Hat
        'crash': InstrumentConfig(0, volume=0.9, pan=0.7),     # Crash Cymbal 1
        'ride': InstrumentConfig(0, volume=0.7, pan=0.7),      # Ride Cymbal 1
        'tom': InstrumentConfig(0, volume=0.8, pan=0.6),       # High Tom
    }
)

# 8-Bit: Chiptune/retro video game aesthetic
EIGHT_BIT = SoundPack(
    name="8-Bit",
    description="Square waves, triangle bass, noise percussion - classic chiptune",
    tempo_range=(120, 140),
    instruments={
        # Melodic instruments (simulating chip sounds with GM)
        'lead': InstrumentConfig(80, volume=0.8, pan=0.6),  # Square Lead
        'bass': InstrumentConfig(82, volume=0.9, pan=0.4),  # Sawtooth Wave (bass)
        'pad': InstrumentConfig(88, volume=0.5, pan=0.5),   # Crystal (pad)
        'pluck': InstrumentConfig(84, volume=0.7, pan=0.7), # Chiff Lead
        'arp': InstrumentConfig(103, volume=0.6, pan=0.3),  # Echo Drops (arp)
        
        # Special effects
        'fanfare': InstrumentConfig(81, volume=0.9, pan=0.5), # Sawtooth Lead (fanfare)
        'stab': InstrumentConfig(85, volume=0.8, pan=0.5),    # Charang (stab)
        
        # Drums (using analog/electronic kit sounds)
        'kick': InstrumentConfig(0, volume=0.9, pan=0.5),     # Electronic kick
        'snare': InstrumentConfig(0, volume=0.8, pan=0.5),    # Electronic snare
        'hihat': InstrumentConfig(0, volume=0.7, pan=0.3),    # Electronic hi-hat
        'crash': InstrumentConfig(0, volume=0.8, pan=0.7),    # Reverse cymbal
        'ride': InstrumentConfig(0, volume=0.6, pan=0.7),     # Electronic ride
        'tom': InstrumentConfig(0, volume=0.7, pan=0.6),      # Electronic tom
    }
)

# Synthwave: 80s-inspired analog synth sounds
SYNTHWAVE = SoundPack(
    name="Synthwave",
    description="Analog pads, gated reverb, side-chain pump - 80s neon aesthetic",
    tempo_range=(100, 118),
    instruments={
        # Melodic instruments (classic analog synth emulation)
        'lead': InstrumentConfig(81, volume=0.8, pan=0.6, reverb=0.3),  # Sawtooth Lead
        'bass': InstrumentConfig(38, volume=0.9, pan=0.4),              # Synth Bass 1
        'pad': InstrumentConfig(91, volume=0.7, pan=0.5, reverb=0.5),   # Warm Pad
        'pluck': InstrumentConfig(87, volume=0.6, pan=0.7),             # Bass & Lead
        'arp': InstrumentConfig(102, volume=0.5, pan=0.3, reverb=0.3),  # Soundtrack arp
        
        # Signature synthwave sounds
        'fanfare': InstrumentConfig(62, volume=0.8, pan=0.5, reverb=0.4), # Synth Brass
        'stab': InstrumentConfig(90, volume=0.7, pan=0.5),                # Polysynth stab
        
        # Drums (gated reverb and electronic emphasis)
        'kick': InstrumentConfig(0, volume=0.9, pan=0.5),      # Punchy electronic kick
        'snare': InstrumentConfig(0, volume=0.8, pan=0.5, reverb=0.6), # Gated reverb snare
        'hihat': InstrumentConfig(0, volume=0.6, pan=0.3),     # Crisp hi-hat
        'crash': InstrumentConfig(0, volume=0.8, pan=0.7, reverb=0.4), # Atmospheric crash
        'ride': InstrumentConfig(0, volume=0.7, pan=0.7),      # Synthetic ride
        'tom': InstrumentConfig(0, volume=0.7, pan=0.6, reverb=0.3),   # Gated tom
    }
)

# 🆕 Tropical Pop: Beach Boys meets Caribbean steel drums
TROPICAL_POP = SoundPack(
    name="Tropical Pop",
    description="Beach Boys meets steel drums - laid-back Caribbean vibes",
    tempo_range=(95, 115),
    instruments={
        # Caribbean melodic instruments
        'lead': InstrumentConfig(114, volume=0.8, pan=0.6, reverb=0.3),  # Steel Drums
        'harmony': InstrumentConfig(12, volume=0.7, pan=0.4, reverb=0.4), # Marimba
        'bass': InstrumentConfig(32, volume=0.9, pan=0.5),               # Acoustic Bass
        'pad': InstrumentConfig(49, volume=0.6, pan=0.5, reverb=0.5),    # String Ensemble
        'arp': InstrumentConfig(11, volume=0.5, pan=0.3, reverb=0.3),    # Vibraphone
        
        # Tropical percussion and effects
        'shaker': InstrumentConfig(0, volume=0.6, pan=0.7),              # Shaker (percussion)
        'bongos': InstrumentConfig(0, volume=0.7, pan=0.3),              # Bongos (percussion)
        'chimes': InstrumentConfig(14, volume=0.5, pan=0.8, reverb=0.6), # Tubular Bells (wind chimes)
        
        # Beach Boys-inspired vocal and brass
        'fanfare': InstrumentConfig(53, volume=0.8, pan=0.5, reverb=0.3), # Voice Oohs (harmony)
        'stab': InstrumentConfig(60, volume=0.7, pan=0.5),                # Muted Trumpet (brass stab)
        
        # Laid-back drums (softer, more relaxed)
        'kick': InstrumentConfig(0, volume=0.8, pan=0.5),      # Softer kick
        'snare': InstrumentConfig(0, volume=0.7, pan=0.5, reverb=0.4), # Brushed snare
        'hihat': InstrumentConfig(0, volume=0.5, pan=0.3),     # Light hi-hat
        'crash': InstrumentConfig(0, volume=0.6, pan=0.7, reverb=0.5), # Gentle splash
        'ride': InstrumentConfig(0, volume=0.6, pan=0.7),      # Light ride
        'tom': InstrumentConfig(0, volume=0.6, pan=0.6, reverb=0.4),   # Warm tom
    }
)

# Master registry of all available packs
SOUND_PACKS: Dict[str, SoundPack] = {
    "Arena Rock": ARENA_ROCK,
    "8-Bit": EIGHT_BIT, 
    "Synthwave": SYNTHWAVE,
    "Tropical Pop": TROPICAL_POP,  # 🆕 Caribbean Kokomo theme
}

# Default pack
DEFAULT_PACK = "Arena Rock"


def get_sound_pack(name: str) -> SoundPack:
    """Get sound pack by name, with fallback to default."""
    return SOUND_PACKS.get(name, SOUND_PACKS[DEFAULT_PACK])


def list_sound_packs() -> Dict[str, str]:
    """List all available sound packs with descriptions."""
    return {name: pack.description for name, pack in SOUND_PACKS.items()}


def validate_sound_pack(name: str) -> bool:
    """Check if sound pack name is valid."""
    return name in SOUND_PACKS