"""
SERP earcon system for audio feedback on search features.
Adds musical cues for podium positions, AI overview, volatility spikes, etc.
"""

from enum import Enum
from typing import List, Dict, Set, Optional
from types import SimpleNamespace
from dataclasses import dataclass
from midiutil import MIDIFile
from .soundpacks import get_sound_pack, SoundPack


class SerpFeature(Enum):
    """SERP features that trigger earcons."""
    PODIUM_WIN = "podium_win"          # Position 1-3
    TOP_POSITION = "top_position"      # Position 1
    TOP_3 = "podium_win"
    TOP_1 = "top_position"
    AI_OVERVIEW = "ai_overview"        # AI overview present
    VIDEO_RESULTS = "video_results"    # Video results present
    VIDEO = "video_results"
    SHOPPING_RESULTS = "shopping"      # Shopping results present
    SHOPPING = "shopping"
    VOLATILITY_SPIKE = "volatility"    # High volatility detected
    POSITION_DROP = "position_drop"    # Position dropped significantly
    TRAFFIC_SURGE = "traffic_surge"    # Click/impression surge


@dataclass
class EarconEvent:
    """An earcon event to be added to the MIDI."""
    feature: SerpFeature
    beat_time: float
    duration: float
    velocity: int = 80
    channel: int = 0


class EarconGenerator:
    """Generates SERP earcons for musical enhancement."""
    
    # Earcon definitions per sound pack
    EARCON_PATTERNS = {
        "Arena Rock": {
            SerpFeature.PODIUM_WIN: {
                'instrument': 56,  # Trumpet fanfare
                'notes': [60, 64, 67, 72],  # C major arpeggio up octave
                'rhythm': [0.0, 0.25, 0.5, 0.75],
                'velocity': 100,
                'duration': 1.0
            },
            SerpFeature.TOP_POSITION: {
                'instrument': 56,  # Trumpet
                'notes': [72, 72, 72],  # Triple high C
                'rhythm': [0.0, 0.33, 0.66],
                'velocity': 110,
                'duration': 1.0
            },
            SerpFeature.VIDEO: {
                'instrument': 31,  # Distortion guitar stab
                'notes': [79, 83, 86],
                'rhythm': [0.0, 0.4, 0.8],
                'velocity': 95,
                'duration': 1.2
            },
            SerpFeature.SHOPPING: {
                'instrument': 12,  # Vibraphone sparkle
                'notes': [84, 88, 91],
                'rhythm': [0.0, 0.5, 0.75],
                'velocity': 75,
                'duration': 1.5
            },
            SerpFeature.AI_OVERVIEW: {
                'instrument': 12,  # Vibraphone bell
                'notes': [84, 88, 91],  # High bell gliss
                'rhythm': [0.0, 0.5, 1.0],
                'velocity': 70,
                'duration': 1.5
            },
            SerpFeature.VOLATILITY_SPIKE: {
                'instrument': 0,   # Will use drums
                'notes': [55, 47, 49],  # Reverse cymbal, tom, crash
                'rhythm': [0.0, 1.0, 1.5],
                'velocity': 90,
                'duration': 2.0,
                'channel': 9  # Drum channel
            }
        },
        "8-Bit": {
            SerpFeature.PODIUM_WIN: {
                'instrument': 80,  # Square wave
                'notes': [72, 76, 79, 84],  # Major triad arp
                'rhythm': [0.0, 0.125, 0.25, 0.375],
                'velocity': 90,
                'duration': 0.5
            },
            SerpFeature.TOP_POSITION: {
                'instrument': 80,  # Square wave
                'notes': [84, 88, 91],  # High triad
                'rhythm': [0.0, 0.1, 0.2],
                'velocity': 100,
                'duration': 0.5
            },
            SerpFeature.VIDEO: {
                'instrument': 81,
                'notes': [76, 79, 83],
                'rhythm': [0.0, 0.25, 0.5],
                'velocity': 95,
                'duration': 0.8
            },
            SerpFeature.SHOPPING: {
                'instrument': 82,
                'notes': [88, 92, 95],
                'rhythm': [0.0, 0.2, 0.4],
                'velocity': 85,
                'duration': 0.8
            },
            SerpFeature.AI_OVERVIEW: {
                'instrument': 88,  # Crystal pad
                'notes': [96, 100, 103],  # Very high bell
                'rhythm': [0.0, 0.25, 0.5],
                'velocity': 60,
                'duration': 1.0
            },
            SerpFeature.VOLATILITY_SPIKE: {
                'instrument': 84,  # Charang (harsh lead)
                'notes': [48, 52, 55],  # Low harsh sweep
                'rhythm': [0.0, 0.5, 1.0],
                'velocity': 80,
                'duration': 1.5
            }
        },
        "Synthwave": {
            SerpFeature.PODIUM_WIN: {
                'instrument': 62,  # Synth brass
                'notes': [60, 63, 67, 72],  # Minor-major progression
                'rhythm': [0.0, 0.33, 0.66, 1.0],
                'velocity': 85,
                'duration': 1.5
            },
            SerpFeature.TOP_POSITION: {
                'instrument': 81,  # Sawtooth lead
                'notes': [72, 75, 79],  # Bright lead stab
                'rhythm': [0.0, 0.25, 0.5],
                'velocity': 95,
                'duration': 1.0
            },
            SerpFeature.VIDEO: {
                'instrument': 98,
                'notes': [82, 85, 89],
                'rhythm': [0.0, 0.3, 0.6],
                'velocity': 90,
                'duration': 1.2
            },
            SerpFeature.SHOPPING: {
                'instrument': 89,
                'notes': [88, 91, 95],
                'rhythm': [0.0, 0.25, 0.5],
                'velocity': 80,
                'duration': 1.2
            },
            SerpFeature.AI_OVERVIEW: {
                'instrument': 88,  # Crystal
                'notes': [84, 87, 91, 96],  # Ethereal cascade
                'rhythm': [0.0, 0.25, 0.5, 0.75],
                'velocity': 65,
                'duration': 2.0
            },
            SerpFeature.VOLATILITY_SPIKE: {
                'instrument': 0,   # Drums
                'notes': [55, 51, 49],  # Reverse, ride, crash
                'rhythm': [0.0, 1.0, 1.5],
                'velocity': 85,
                'duration': 2.0,
                'channel': 9
            }
        },
        # 🆕 Tropical Pop: Caribbean Kokomo theme earcons
        "Tropical Pop": {
            SerpFeature.PODIUM_WIN: {
                'instrument': 114,  # Steel Drums
                'notes': [60, 64, 67, 72],  # C major arpeggio with Caribbean flair
                'rhythm': [0.0, 0.3, 0.6, 0.9],  # Laid-back timing
                'velocity': 80,
                'duration': 1.8
            },
            SerpFeature.TOP_POSITION: {
                'instrument': 114,  # Steel Drums
                'notes': [72, 76, 79],  # High celebration roll
                'rhythm': [0.0, 0.2, 0.4],
                'velocity': 90,
                'duration': 1.2
            },
            SerpFeature.VIDEO: {
                'instrument': 11,
                'notes': [79, 83, 86],
                'rhythm': [0.0, 0.35, 0.7],
                'velocity': 85,
                'duration': 1.4
            },
            SerpFeature.SHOPPING: {
                'instrument': 13,
                'notes': [67, 71, 74],
                'rhythm': [0.0, 0.25, 0.5],
                'velocity': 75,
                'duration': 1.4
            },
            SerpFeature.AI_OVERVIEW: {
                'instrument': 11,   # Vibraphone (crystal ping)
                'notes': [84, 88, 91],  # High crystalline bell
                'rhythm': [0.0, 0.5, 1.0],
                'velocity': 60,
                'duration': 1.5
            },
            SerpFeature.VOLATILITY_SPIKE: {
                'instrument': 14,   # Tubular Bells (wind chimes)
                'notes': [96, 91, 84, 79],  # Descending chime cascade
                'rhythm': [0.0, 0.3, 0.6, 0.9],
                'velocity': 70,
                'duration': 2.0
            }
        }
    }
    
    def __init__(self, sound_pack_name: str = "Arena Rock"):
        self.sound_pack_name = sound_pack_name
        self.sound_pack = get_sound_pack(sound_pack_name)
        
    def detect_serp_features(self, query_data: Dict) -> Set[SerpFeature]:
        """Detect SERP features from query data."""
        features = set()
        
        # Position-based features
        position = query_data.get('current_position', query_data.get('position', 10))
        if isinstance(position, (int, float)):
            if position == 1:
                features.add(SerpFeature.TOP_POSITION)
                features.add(SerpFeature.PODIUM_WIN)
            elif position <= 3:
                features.add(SerpFeature.PODIUM_WIN)
        
        # SERP analysis features
        serp_analysis = query_data.get('serp_analysis', {})
        if serp_analysis.get('ai_overview'):
            features.add(SerpFeature.AI_OVERVIEW)
        if serp_analysis.get('video_results', 0) > 0:
            features.add(SerpFeature.VIDEO_RESULTS)
        if serp_analysis.get('shopping_results', 0) > 0:
            features.add(SerpFeature.SHOPPING_RESULTS)
            
        # Movement and volatility
        ranking_change = query_data.get('ranking_change', 0)
        if ranking_change < -2:  # Dropped more than 2 positions
            features.add(SerpFeature.POSITION_DROP)
            
        volatility = query_data.get('volatility_index', query_data.get('volatility', 0))
        if volatility > 0.6:
            features.add(SerpFeature.VOLATILITY_SPIKE)
            
        # Traffic metrics
        click_change = query_data.get('click_change_percent', 0)
        impression_change = query_data.get('impression_change_percent', 0)
        if click_change > 50 or impression_change > 50:
            features.add(SerpFeature.TRAFFIC_SURGE)
            
        return features
    
    def generate_earcons_for_section(self, 
                                   features: Set[SerpFeature], 
                                   section_start_beat: float,
                                   section_duration_beats: float) -> List[EarconEvent]:
        """Generate earcon events for a musical section."""
        if not features:
            return []
            
        events = []
        feature_list = list(features)
        
        # Space earcons across the section
        for i, feature in enumerate(feature_list):
            # Distribute timing across section
            relative_time = (i + 0.5) / len(feature_list)  # Avoid start/end
            beat_time = section_start_beat + (relative_time * section_duration_beats)
            
            earcon_events = self._create_earcon_events(feature, beat_time)
            events.extend(earcon_events)
            
        return events
    
    def _create_earcon_events(self, feature: SerpFeature, start_beat: float) -> List[EarconEvent]:
        """Create MIDI events for a specific earcon."""
        pattern = self.EARCON_PATTERNS.get(self.sound_pack_name, {}).get(feature)
        if not pattern:
            return []  # No pattern defined for this feature/pack combo
            
        events = []
        notes = pattern['notes']
        rhythms = pattern['rhythm']
        instrument = pattern['instrument']
        velocity = pattern['velocity']
        channel = pattern.get('channel', 0)
        note_duration = pattern['duration'] / len(notes)  # Divide total duration
        
        for note, rhythm_offset in zip(notes, rhythms):
            event_time = start_beat + rhythm_offset
            
            event = EarconEvent(
                feature=feature,
                beat_time=event_time,
                duration=note_duration,
                velocity=velocity,
                channel=channel
            )
            events.append(event)
            
        return events
    
    def add_earcons_to_midi(self, 
                           midi: MIDIFile, 
                           events: List[EarconEvent], 
                           track: int = 0) -> None:
        """Add earcon events to MIDI file."""
        # Group events by instrument/channel for program changes
        instruments_used = {}
        
        for event in events:
            pattern = self.EARCON_PATTERNS.get(self.sound_pack_name, {}).get(event.feature, {})
            if not pattern:
                continue
                
            instrument = pattern['instrument']
            channel = pattern.get('channel', 0)
            
            # Set program change if needed
            if (channel, instrument) not in instruments_used:
                if channel != 9:  # Skip drum channel program changes
                    midi.addProgramChange(track, channel, event.beat_time, instrument)
                instruments_used[(channel, instrument)] = True
            
            # Add the notes for this earcon
            notes = pattern['notes']
            rhythms = pattern['rhythm']
            note_duration = event.duration / len(notes)
            
            for note, rhythm_offset in zip(notes, rhythms):
                note_time = event.beat_time + rhythm_offset
                
                midi.addNote(track, channel, note, note_time, note_duration, event.velocity)
                midi.tracks[track].eventList.append(
                    SimpleNamespace(
                        type="earcon",
                        feature=event.feature.value,
                        pitch=note,
                        time=note_time,
                        channel=channel,
                        velocity=event.velocity,
                    )
                )


def create_earcon_generator(sound_pack_name: str) -> EarconGenerator:
    """Factory function to create earcon generator."""
    return EarconGenerator(sound_pack_name)


def detect_query_features(query_data: Dict) -> Set[SerpFeature]:
    """Convenience function to detect features from query data."""
    generator = EarconGenerator()
    return generator.detect_serp_features(query_data)

for _patterns in EarconGenerator.EARCON_PATTERNS.values():
    if SerpFeature.VIDEO_RESULTS in _patterns:
        _patterns.setdefault(SerpFeature.VIDEO, _patterns[SerpFeature.VIDEO_RESULTS])
    if SerpFeature.SHOPPING_RESULTS in _patterns:
        _patterns.setdefault(SerpFeature.SHOPPING, _patterns[SerpFeature.SHOPPING_RESULTS])
    if SerpFeature.TOP_POSITION in _patterns:
        _patterns.setdefault(SerpFeature.TOP_1, _patterns[SerpFeature.TOP_POSITION])
    if SerpFeature.PODIUM_WIN in _patterns:
        _patterns.setdefault(SerpFeature.TOP_3, _patterns[SerpFeature.PODIUM_WIN])


def add_serp_earcons(
    midi: MIDIFile,
    track: int,
    features: List[SerpFeature] | Set[SerpFeature],
    section_duration_beats: float,
    sound_pack_name: str = "Arena Rock",
    section_start_beat: float = 0.0,
) -> List[EarconEvent]:
    """Add SERP earcons directly to a MIDI track and return generated events."""
    feature_set = set(features)
    generator = EarconGenerator(sound_pack_name)
    events = generator.generate_earcons_for_section(feature_set, section_start_beat, section_duration_beats)
    generator.add_earcons_to_midi(midi, events, track)
    return events


EARCON_INSTRUMENTS = {
    feature: (
        pattern.get("instrument", 0),
        pattern.get("notes", [0])[0] if pattern.get("notes") else 0,
    )
    for pack in EarconGenerator.EARCON_PATTERNS.values()
    for feature, pattern in pack.items()
}
