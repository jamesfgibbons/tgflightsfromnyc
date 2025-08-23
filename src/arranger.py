"""
Musical arrangement system for SERP Radio.
Organizes sonification into musical sections with key changes and tempo modulation.
"""

import random
from enum import Enum
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from midiutil import MIDIFile


class Key(Enum):
    """Musical keys for momentum mapping."""
    C_MAJOR = "C_MAJOR"
    A_MINOR = "A_MINOR" 
    C_LYDIAN = "C_LYDIAN"


class SectionType(Enum):
    """Musical section types."""
    INTRO = "intro"
    BODY_A = "body_a"
    BRIDGE = "bridge"
    BODY_B = "body_b"
    OUTRO = "outro"


@dataclass
class MusicSection:
    """A musical section with metadata."""
    section_type: SectionType
    bars: int
    start_bar: int
    key: Key
    tempo: int
    momentum_score: float
    
    @property
    def start_beat(self) -> float:
        """Start time in beats (4 beats per bar)."""
        return self.start_bar * 4.0
        
    @property
    def duration_beats(self) -> float:
        """Duration in beats."""
        return self.bars * 4.0


class MusicArranger:
    """Arranges momentum data into musical sections with keys and tempo."""
    
    # Scale definitions (MIDI note numbers relative to root)
    SCALES = {
        Key.C_MAJOR: [0, 2, 4, 5, 7, 9, 11],      # Bright, positive
        Key.A_MINOR: [9, 11, 0, 2, 4, 5, 7],      # Melancholic, negative
        Key.C_LYDIAN: [0, 2, 4, 6, 7, 9, 11],     # Dreamy, neutral
    }
    
    # Chord progressions for each key
    CHORD_PROGRESSIONS = {
        Key.C_MAJOR: [
            [60, 64, 67],  # C Major
            [57, 60, 64],  # A minor
            [62, 65, 69],  # D minor 
            [67, 71, 74],  # G Major
        ],
        Key.A_MINOR: [
            [57, 60, 64],  # A minor
            [62, 65, 69],  # D minor
            [60, 64, 67],  # C Major
            [67, 71, 74],  # G Major
        ],
        Key.C_LYDIAN: [
            [60, 64, 67, 71],  # C Maj7
            [62, 66, 69, 73],  # D Maj7
            [64, 68, 71, 75],  # E min7
            [66, 69, 73, 76],  # F# min7b5
        ],
    }
    
    def __init__(self, total_bars: int = 32, base_tempo: int = 116):
        self.total_bars = total_bars
        self.base_tempo = base_tempo
        self.sections: List[MusicSection] = []
        
    def build_default_sections(self, total_bars: int) -> List[MusicSection]:
        """
        Build default musical sections when no momentum data is available.
        
        Args:
            total_bars: Total number of bars to allocate
            
        Returns:
            List of MusicSection objects covering total_bars
        """
        # Use standard section allocation
        original_total = self.total_bars
        self.total_bars = total_bars
        section_bars = self._allocate_section_bars()
        self.total_bars = original_total  # Restore original
        
        # Ensure we don't exceed total_bars
        if sum(section_bars) > total_bars:
            # Truncate sections to fit
            allocated = 0
            truncated_bars = []
            for bars in section_bars:
                remaining = total_bars - allocated
                if remaining <= 0:
                    break
                actual_bars = min(bars, remaining)
                truncated_bars.append(actual_bars)
                allocated += actual_bars
            section_bars = truncated_bars
        
        # Create sections with neutral/balanced settings
        sections = []
        current_bar = 0
        section_types = [SectionType.INTRO, SectionType.BODY_A, SectionType.BRIDGE, 
                        SectionType.BODY_B, SectionType.OUTRO]
        
        for i, bars in enumerate(section_bars):
            if i >= len(section_types):
                break  # Don't exceed available section types
                
            section_type = section_types[i]
            
            section = MusicSection(
                section_type=section_type,
                bars=bars,
                start_bar=current_bar,
                key=Key.C_MAJOR,  # Default to bright key
                tempo=self.base_tempo,
                momentum_score=0.5  # Neutral momentum
            )
            
            sections.append(section)
            current_bar += bars
            
        return sections

    def arrange_momentum_data(self, momentum_data: List[Dict]) -> List[MusicSection]:
        """Arrange momentum data into musical sections with fallback safety."""
        # Fallback to defaults if no momentum data or too short
        if not momentum_data or len(momentum_data) < 2:
            return self.build_default_sections(self.total_bars)
            
        # Calculate section allocation
        section_bars = self._allocate_section_bars()
        
        # Create sections based on momentum
        sections = []
        current_bar = 0
        
        section_types = [SectionType.INTRO, SectionType.BODY_A, SectionType.BRIDGE, 
                        SectionType.BODY_B, SectionType.OUTRO]
        
        # Ensure we have at least 3 musical sections even with limited momentum data
        for i, (section_type, bars) in enumerate(zip(section_types, section_bars)):
            # Distribute momentum data across sections intelligently
            if len(momentum_data) == 1:
                # Single momentum point - use for all sections
                momentum = momentum_data[0]
            elif len(momentum_data) == 2:
                # Two points - spread across intro/body and outro
                momentum_idx = 0 if i < 3 else 1
                momentum = momentum_data[momentum_idx]
            else:
                # Multiple points - distribute proportionally
                momentum_idx = min(i * len(momentum_data) // len(section_types), 
                                 len(momentum_data) - 1)
                momentum = momentum_data[momentum_idx]
            
            momentum_score = self._extract_momentum_score(momentum)
            key = self._select_key_for_momentum(momentum_score)
            tempo = self._calculate_tempo(momentum_score, section_type)
            
            section = MusicSection(
                section_type=section_type,
                bars=bars,
                start_bar=current_bar,
                key=key,
                tempo=tempo,
                momentum_score=momentum_score
            )
            
            sections.append(section)
            current_bar += bars
            
        self.sections = sections
        return sections
    
    def _allocate_section_bars(self) -> List[int]:
        """Allocate bars to each section type."""
        if self.total_bars <= 16:
            # Short form
            return [2, 4, 2, 4, 4]  # 16 bars total
        elif self.total_bars <= 24:
            # Medium form  
            return [4, 6, 2, 6, 6]  # 24 bars total
        else:
            # Full form
            intro_bars = 4
            outro_bars = max(4, self.total_bars // 8)
            remaining = self.total_bars - intro_bars - outro_bars
            
            body_a_bars = remaining // 3
            bridge_bars = max(2, remaining // 6)
            body_b_bars = remaining - body_a_bars - bridge_bars
            
            return [intro_bars, body_a_bars, bridge_bars, body_b_bars, outro_bars]
    
    def _extract_momentum_score(self, momentum_data: Dict) -> float:
        """Extract momentum score from data (0.0 = negative, 1.0 = positive)."""
        if not momentum_data:
            return 0.5
            
        # Try various fields that might contain momentum info
        label = momentum_data.get('label', '').lower()
        if 'positive' in label or 'momentum_pos' in label:
            return 0.8
        elif 'negative' in label or 'momentum_neg' in label:
            return 0.2
        elif 'volatile' in label:
            return 0.6
            
        # Try numeric fields
        ctr = momentum_data.get('normalized_ctr', momentum_data.get('ctr', 0.5))
        position = momentum_data.get('normalized_position', momentum_data.get('position', 0.5))
        
        # Average available metrics
        return (float(ctr) + float(position)) / 2.0
    
    def _select_key_for_momentum(self, momentum_score: float) -> Key:
        """Select musical key based on momentum."""
        if momentum_score > 0.7:
            return Key.C_MAJOR  # Positive, bright
        elif momentum_score < 0.3:
            return Key.A_MINOR  # Negative, melancholic
        else:
            return Key.C_LYDIAN  # Neutral, dreamy
    
    def _calculate_tempo(self, momentum_score: float, section_type: SectionType) -> int:
        """Calculate tempo based on momentum and section type."""
        # Base tempo modulation
        tempo_mod = (momentum_score - 0.5) * 20  # ±10 BPM range
        
        # Section-specific adjustments
        section_adjustments = {
            SectionType.INTRO: -4,      # Slightly slower build
            SectionType.BODY_A: 0,      # Normal tempo
            SectionType.BRIDGE: -2,     # Slight pullback
            SectionType.BODY_B: 2,      # Push forward
            SectionType.OUTRO: -6,      # Slower resolution
        }
        
        tempo = self.base_tempo + tempo_mod + section_adjustments[section_type]
        return max(80, min(160, int(tempo)))  # Clamp to reasonable range
    
    def _create_default_arrangement(self) -> List[MusicSection]:
        """Create a default arrangement when no momentum data is available."""
        section_bars = self._allocate_section_bars()
        sections = []
        current_bar = 0
        
        section_types = [SectionType.INTRO, SectionType.BODY_A, SectionType.BRIDGE,
                        SectionType.BODY_B, SectionType.OUTRO]
        
        for section_type, bars in zip(section_types, section_bars):
            section = MusicSection(
                section_type=section_type,
                bars=bars,
                start_bar=current_bar,
                key=Key.C_MAJOR,
                tempo=self.base_tempo,
                momentum_score=0.5
            )
            sections.append(section)
            current_bar += bars
            
        return sections
    
    def generate_chord_progression(self, key: Key, bars: int) -> List[List[int]]:
        """Generate chord progression for a section."""
        base_chords = self.CHORD_PROGRESSIONS[key]
        chords = []
        
        for bar in range(bars):
            chord_idx = bar % len(base_chords)
            chord = base_chords[chord_idx].copy()
            chords.append(chord)
            
        return chords
    
    def add_section_transitions(self, midi: MIDIFile, track: int = 0) -> None:
        """Add drum fills and transitions between sections."""
        if not self.sections:
            return
            
        for i, section in enumerate(self.sections[:-1]):  # Skip last section
            # Add drum fill at end of section
            fill_start = section.start_beat + section.duration_beats - 2.0  # Last 2 beats
            self._add_drum_fill(midi, track, fill_start, 2.0)
            
            # Add rise SFX when transitioning to positive momentum
            next_section = self.sections[i + 1]
            if (section.momentum_score < 0.7 and 
                next_section.momentum_score > 0.7):
                self._add_rise_sfx(midi, track, fill_start, 2.0)
    
    def _add_drum_fill(self, midi: MIDIFile, track: int, start_beat: float, duration: float) -> None:
        """Add a drum fill."""
        # Tom-tom pattern
        tom_notes = [47, 48, 50]  # Low, mid, high toms
        beats_per_tom = duration / len(tom_notes)
        
        for i, tom_note in enumerate(tom_notes):
            beat_time = start_beat + (i * beats_per_tom)
            midi.addNote(track, 9, tom_note, beat_time, beats_per_tom * 0.8, 100)
            
        # Crash at the end
        crash_time = start_beat + duration - 0.25
        midi.addNote(track, 9, 49, crash_time, 0.5, 110)  # Crash cymbal
    
    def _add_rise_sfx(self, midi: MIDIFile, track: int, start_beat: float, duration: float) -> None:
        """Add rising SFX for positive momentum transitions."""
        # Reverse cymbal effect (simulated with volume automation)
        for i in range(8):
            beat_time = start_beat + (i * duration / 8)
            velocity = int(40 + (i * 10))  # Growing volume
            midi.addNote(track, 9, 55, beat_time, duration / 8, velocity)  # Splash cymbal
    
    def get_total_duration_beats(self) -> float:
        """Get total arrangement duration in beats."""
        return sum(section.duration_beats for section in self.sections)
    
    def get_total_duration_seconds(self, average_tempo: Optional[int] = None) -> float:
        """Get total arrangement duration in seconds."""
        if not self.sections:
            return 0.0
            
        if average_tempo is None:
            average_tempo = sum(s.tempo for s in self.sections) // len(self.sections)
            
        total_beats = self.get_total_duration_beats()
        beats_per_second = average_tempo / 60.0
        return total_beats / beats_per_second