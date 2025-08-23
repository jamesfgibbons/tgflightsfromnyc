"""
Core sonification module for SERP Loop Radio.
Converts DataFrame to MIDI using FATLD (Frequency, Amplitude, Timbre, Location, Duration) mappings.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List
from midiutil import MIDIFile
import logging

from .mappings import MusicMappings, validate_midi_values, beats_to_ticks

logger = logging.getLogger(__name__)


class SERPSonifier:
    """Main class for converting SERP data to MIDI."""
    
    def __init__(self, config_path: Path = None):
        """Initialize sonifier with mapping configuration."""
        self.mappings = MusicMappings(config_path)
        self.config = self.mappings.config
        
        # Audio configuration
        self.audio_config = self.config.get("audio", {})
        self.tempo = self.audio_config.get("tempo", 112)
        self.time_signature = self.audio_config.get("time_signature", [4, 4])
        self.total_bars = self.audio_config.get("total_bars", 16)
        self.ticks_per_beat = 480
        
        # Musical scale setup
        self.root_note = "C"
        self.scale = "pentatonic"
        self.scale_notes = self.mappings.get_scale_notes(self.root_note, self.scale)
        
        logger.info(f"Initialized sonifier: {self.tempo} BPM, {self.total_bars} bars")
    
    def csv_to_midi(
        self, 
        df: pd.DataFrame, 
        output_path: Path,
        bass_riff_path: Optional[Path] = None
    ) -> Path:
        """
        Convert DataFrame to MIDI file using FATLD mappings.
        
        Args:
            df: Processed SERP data
            output_path: Path for output MIDI file
            bass_riff_path: Optional path to bass riff MIDI file
            
        Returns:
            Path to created MIDI file
        """
        logger.info(f"Converting {len(df)} SERP records to MIDI")
        
        # Create MIDI file with multiple tracks
        num_tracks = len(df['engine'].unique()) + 2  # +1 for percussion, +1 for bass
        midi_file = MIDIFile(num_tracks)
        
        # Set tempo and time signature
        midi_file.addTempo(0, 0, self.tempo)
        midi_file.addTimeSignature(0, 0, *self.time_signature)
        
        # Track assignments
        track_map = self._create_track_mapping(df)
        
        # Process each row
        for idx, row in df.iterrows():
            self._add_midi_event(midi_file, row, track_map, idx)
        
        # Add bass riff if conditions are met
        if bass_riff_path and self._should_add_bass_riff(df):
            self._add_bass_riff(midi_file, bass_riff_path, track_map['bass'])
        
        # Add percussion for anomalies
        self._add_anomaly_percussion(midi_file, df, track_map['percussion'])
        
        # Write MIDI file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            midi_file.writeFile(f)
        
        logger.info(f"Created MIDI file: {output_path}")
        return output_path
    
    def _create_track_mapping(self, df: pd.DataFrame) -> Dict[str, int]:
        """Create mapping of engines to MIDI tracks."""
        engines = list(df['engine'].unique())
        track_map = {}
        
        # Assign tracks to engines
        for i, engine in enumerate(engines):
            track_map[engine] = i
            
        # Special tracks
        track_map['percussion'] = len(engines)
        track_map['bass'] = len(engines) + 1
        
        return track_map
    
    def _add_midi_event(
        self, 
        midi_file: MIDIFile, 
        row: pd.Series, 
        track_map: Dict[str, int],
        event_index: int
    ) -> None:
        """Add a single MIDI event based on row data."""
        
        # Get track for this engine
        track = track_map.get(row['engine'], 0)
        
        # FATLD Mapping
        # Frequency (Pitch)
        base_note = 60  # Middle C
        pitch_adjustment = self.mappings.get_pitch_from_rank_delta(row.get('rank_delta', 0))
        midi_note = base_note + pitch_adjustment
        midi_note = self.mappings.fit_to_scale(midi_note, self.scale_notes)
        
        # Amplitude (Velocity)
        velocity = self.mappings.get_velocity_from_share(row.get('share_pct', 0.5))
        
        # Timbre (Instrument)
        instrument = self.mappings.get_instrument_from_engine(row['engine'])
        midi_file.addProgramChange(track, 0, 0, instrument)
        
        # Location (Pan) - stored as controller message
        pan_value = self.mappings.get_pan_from_segment(row.get('segment', 'Central'))
        # Convert pan to MIDI controller value (0-127, 64 = center)
        midi_pan = int(64 + pan_value * 64 / 100)
        midi_pan = max(0, min(127, midi_pan))
        
        # Duration
        duration = self.mappings.get_duration_from_rich_type(row.get('rich_type', ''))
        
        # Timing - distribute events across bars
        beats_per_bar = self.time_signature[0]
        total_beats = self.total_bars * beats_per_bar
        
        # Calculate start time based on event index
        start_beat = (event_index / len(df.index)) * total_beats
        start_beat = self.mappings.quantize_to_grid(start_beat, 0.25)  # 16th note grid
        
        # Validate MIDI values
        midi_note, velocity, _ = validate_midi_values(midi_note, velocity)
        
        # Add MIDI events
        midi_file.addNote(
            track=track,
            channel=0,
            pitch=midi_note,
            time=start_beat,
            duration=duration,
            volume=velocity
        )
        
        # Add pan controller
        midi_file.addControllerEvent(
            track=track,
            channel=0,
            time=start_beat,
            controller_number=10,  # Pan controller
            parameter=midi_pan
        )
        
        # Add brand emphasis if this is brand domain
        brand_domain = os.getenv('BRAND_DOMAIN', 'mybrand.com')
        if brand_domain in row.get('domain', '') and row.get('rank_absolute', 100) <= 3:
            # Add octave doubling for brand wins
            octave_note, _, _ = validate_midi_values(midi_note + 12, velocity - 20)
            midi_file.addNote(
                track=track,
                channel=0,
                pitch=octave_note,
                time=start_beat,
                duration=duration,
                volume=velocity - 20
            )
    
    def _should_add_bass_riff(self, df: pd.DataFrame) -> bool:
        """Check if bass riff should be added based on brand performance."""
        bass_config = self.config.get("bass_riff", {})
        
        if not bass_config.get("enabled", False):
            return False
        
        # Check if brand has top 3 rankings
        brand_domain = os.getenv('BRAND_DOMAIN', 'mybrand.com')
        brand_rows = df[df['domain'].str.contains(brand_domain, na=False)]
        
        if brand_rows.empty:
            return False
        
        top_3_count = len(brand_rows[brand_rows['rank_absolute'] <= 3])
        return top_3_count > 0
    
    def _add_bass_riff(
        self, 
        midi_file: MIDIFile, 
        riff_path: Path, 
        bass_track: int
    ) -> None:
        """Add pre-recorded bass riff to the MIDI file."""
        # For MVP, create a simple bass pattern
        # In production, would load and transpose actual MIDI file
        logger.info("Adding bass riff pattern")
        
        bass_config = self.config.get("bass_riff", {})
        root_note = bass_config.get("root_note", "C")
        
        # Simple bass pattern in the root key
        bass_root = self.mappings.NOTE_TO_MIDI.get(root_note, 36)  # Low C
        bass_pattern = [
            (0, bass_root, 1.0),      # Beat 1
            (2, bass_root + 7, 0.5),  # Beat 3
            (4, bass_root, 1.0),      # Beat 1 (next bar)
            (6, bass_root + 5, 0.5),  # Beat 3
        ]
        
        # Set bass instrument
        midi_file.addProgramChange(bass_track, 0, 0, 33)  # Electric Bass (finger)
        
        # Add pattern across multiple bars
        for bar in range(0, self.total_bars, 4):  # Every 4 bars
            for beat_offset, note, duration in bass_pattern:
                start_time = bar * self.time_signature[0] + beat_offset
                if start_time < self.total_bars * self.time_signature[0]:
                    midi_file.addNote(
                        track=bass_track,
                        channel=1,
                        pitch=note,
                        time=start_time,
                        duration=duration,
                        volume=100
                    )
    
    def _add_anomaly_percussion(
        self, 
        midi_file: MIDIFile, 
        df: pd.DataFrame, 
        percussion_track: int
    ) -> None:
        """Add percussion hits for detected anomalies."""
        anomaly_rows = df[df.get('anomaly', False)]
        
        if anomaly_rows.empty:
            return
        
        logger.info(f"Adding percussion for {len(anomaly_rows)} anomalies")
        
        # Set drum kit on channel 9 (10 in 1-indexed)
        for idx, row in anomaly_rows.iterrows():
            # Calculate timing
            event_index = df.index.get_loc(idx)
            total_beats = self.total_bars * self.time_signature[0]
            start_beat = (event_index / len(df)) * total_beats
            start_beat = self.mappings.quantize_to_grid(start_beat, 0.25)
            
            # Add rim shot for anomaly
            percussion_note = self.mappings.get_anomaly_percussion()
            midi_file.addNote(
                track=percussion_track,
                channel=9,  # Standard MIDI drum channel
                pitch=percussion_note,
                time=start_beat,
                duration=0.25,
                volume=127
            )
    
    def create_sample_midi(self, output_path: Path) -> Path:
        """Create a sample MIDI file for testing."""
        sample_data = {
            'keyword': ['ai chatbot', 'customer service', 'help desk'],
            'engine': ['google_web', 'google_ai', 'google_web'],
            'rank_delta': [-2, 1, 0],
            'share_pct': [0.3, 0.1, 0.2],
            'segment': ['Central', 'West', 'East'],
            'rich_type': ['', 'video', 'shopping_pack'],
            'anomaly': [False, True, False],
            'domain': ['openai.com', 'intercom.com', 'zendesk.com']
        }
        
        df = pd.DataFrame(sample_data)
        return self.csv_to_midi(df, output_path)


def csv_to_midi(
    df: pd.DataFrame, 
    config_path: Path, 
    bass_riff_path: Optional[Path] = None
) -> Path:
    """
    Main function to convert CSV to MIDI.
    
    Args:
        df: Processed SERP DataFrame
        config_path: Path to mapping configuration
        bass_riff_path: Optional bass riff MIDI file
        
    Returns:
        Path to generated MIDI file
    """
    sonifier = SERPSonifier(config_path)
    
    # Generate output filename
    output_dir = Path(os.getenv('TMP_DIR', '/tmp'))
    output_path = output_dir / f"serp_audio_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.mid"
    
    return sonifier.csv_to_midi(df, output_path, bass_riff_path)


if __name__ == "__main__":
    # Test sonification
    sonifier = SERPSonifier(Path("config/mapping.json"))
    
    # Create sample MIDI
    output_path = Path("/tmp/test_serp.mid")
    sonifier.create_sample_midi(output_path)
    
    print(f"Created test MIDI file: {output_path}")
    
    # Test the mapping functionality
    sample_df = pd.DataFrame({
        'keyword': ['ai chatbot'] * 5,
        'engine': ['google_web', 'google_ai', 'openai', 'perplexity', 'google_web'],
        'rank_delta': [-3, 0, 2, -1, 1],
        'share_pct': [0.4, 0.2, 0.1, 0.15, 0.15],
        'segment': ['Central', 'West', 'East', 'Central', 'West'],
        'rich_type': ['', 'video', '', 'shopping_pack', ''],
        'anomaly': [True, False, False, False, False],
        'domain': ['mybrand.com', 'competitor1.com', 'openai.com', 'perplexity.ai', 'other.com']
    })
    
    midi_path = sonifier.csv_to_midi(sample_df, Path("/tmp/sample_serp.mid"))
    print(f"Created sample MIDI: {midi_path}") 