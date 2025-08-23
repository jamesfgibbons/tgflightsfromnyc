"""
Unit tests for extract_bars.py
"""

import json
import tempfile
import unittest
from pathlib import Path
import pretty_midi
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from extract_bars import extract_bars_from_midi, _create_bar_fingerprint


class TestExtractBars(unittest.TestCase):
    """Test bar extraction functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.tenant_id = "test_tenant"
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_synthetic_midi(self, bars: int = 4, tempo: float = 120.0) -> str:
        """Create synthetic MIDI file with specified number of bars."""
        midi_data = pretty_midi.PrettyMIDI(initial_tempo=tempo)
        
        # Create a simple instrument
        instrument = pretty_midi.Instrument(program=0, name="Test")
        
        beat_duration = 60.0 / tempo  # Duration of one quarter note
        bar_duration = beat_duration * 4  # 4/4 time
        
        # Add notes across the specified number of bars
        for bar in range(bars):
            bar_start = bar * bar_duration
            
            # Add a chord at the start of each bar
            chord_pitches = [60, 64, 67]  # C major
            for pitch in chord_pitches:
                note = pretty_midi.Note(
                    velocity=80,
                    pitch=pitch,
                    start=bar_start,
                    end=bar_start + beat_duration
                )
                instrument.notes.append(note)
            
            # Add a melody note in the middle of the bar
            melody_note = pretty_midi.Note(
                velocity=90,
                pitch=72 + bar,  # Rising melody
                start=bar_start + beat_duration * 2,
                end=bar_start + beat_duration * 3
            )
            instrument.notes.append(melody_note)
        
        midi_data.instruments.append(instrument)
        
        # Save to temporary file
        temp_path = os.path.join(self.temp_dir, f"test_{bars}bars.mid")
        midi_data.write(temp_path)
        return temp_path
    
    def test_extract_bars_basic(self):
        """Test basic bar extraction from synthetic MIDI."""
        midi_path = self._create_synthetic_midi(bars=4, tempo=120.0)
        result = extract_bars_from_midi(midi_path, self.tenant_id)
        
        # Verify basic structure
        self.assertFalse(result.get("error", True))
        self.assertEqual(result["tenant_id"], self.tenant_id)
        self.assertIn("bars", result)
        self.assertIn("total_bars", result)
        
        # Should have 4 bars
        self.assertEqual(result["total_bars"], 4)
        self.assertEqual(len(result["bars"]), 4)
        
        # Check first bar structure
        first_bar = result["bars"][0]
        required_fields = ["bar_index", "time_signature", "start_sec", "end_sec", "bpm", "notes", "hash"]
        for field in required_fields:
            self.assertIn(field, first_bar)
        
        # Verify timing
        self.assertEqual(first_bar["bar_index"], 0)
        self.assertEqual(first_bar["start_sec"], 0.0)
        self.assertGreater(first_bar["end_sec"], 0.0)
        self.assertEqual(first_bar["bpm"], 120.0)
        
        # Each bar should have notes (chord + melody)
        self.assertGreater(len(first_bar["notes"]), 0)
    
    def test_extract_bars_tempo_change(self):
        """Test bar extraction with tempo changes."""
        # Create MIDI with tempo change
        midi_data = pretty_midi.PrettyMIDI(initial_tempo=120.0)
        instrument = pretty_midi.Instrument(program=0)
        
        # Add tempo change at 2 seconds
        midi_data._tick_scales = [(0.0, 120.0), (2.0, 140.0)]
        
        # Add notes spanning the tempo change
        for i in range(4):
            note = pretty_midi.Note(
                velocity=80,
                pitch=60 + i,
                start=i * 0.6,
                end=(i * 0.6) + 0.5
            )
            instrument.notes.append(note)
        
        midi_data.instruments.append(instrument)
        
        temp_path = os.path.join(self.temp_dir, "tempo_change.mid")
        midi_data.write(temp_path)
        
        result = extract_bars_from_midi(temp_path, self.tenant_id)
        
        self.assertFalse(result.get("error", True))
        self.assertGreater(result["total_bars"], 0)
    
    def test_fingerprinting_consistency(self):
        """Test that identical bars produce identical fingerprints."""
        notes1 = [
            {"pitch": 60, "velocity": 80, "start": 0.0, "duration": 1.0},
            {"pitch": 64, "velocity": 80, "start": 1.0, "duration": 1.0}
        ]
        
        notes2 = [
            {"pitch": 60, "velocity": 80, "start": 0.0, "duration": 1.0},
            {"pitch": 64, "velocity": 80, "start": 1.0, "duration": 1.0}
        ]
        
        hash1 = _create_bar_fingerprint(notes1)
        hash2 = _create_bar_fingerprint(notes2)
        
        self.assertEqual(hash1, hash2)
    
    def test_fingerprinting_difference(self):
        """Test that different bars produce different fingerprints."""
        notes1 = [
            {"pitch": 60, "velocity": 80, "start": 0.0, "duration": 1.0}
        ]
        
        notes2 = [
            {"pitch": 61, "velocity": 80, "start": 0.0, "duration": 1.0}  # Different pitch
        ]
        
        hash1 = _create_bar_fingerprint(notes1)
        hash2 = _create_bar_fingerprint(notes2)
        
        self.assertNotEqual(hash1, hash2)
    
    def test_empty_midi_error(self):
        """Test handling of MIDI files with no instruments."""
        midi_data = pretty_midi.PrettyMIDI()
        temp_path = os.path.join(self.temp_dir, "empty.mid")
        midi_data.write(temp_path)
        
        result = extract_bars_from_midi(temp_path, self.tenant_id)
        
        self.assertTrue(result.get("error", False))
        self.assertEqual(result["tenant_id"], self.tenant_id)
        self.assertIn("message", result)
    
    def test_nonexistent_file_error(self):
        """Test handling of nonexistent files."""
        nonexistent_path = "/nonexistent/file.mid"
        result = extract_bars_from_midi(nonexistent_path, self.tenant_id)
        
        self.assertTrue(result.get("error", False))
        self.assertEqual(result["tenant_id"], self.tenant_id)
        self.assertIn("message", result)
    
    def test_json_output_validity(self):
        """Test that output is valid JSON."""
        midi_path = self._create_synthetic_midi(bars=2)
        result = extract_bars_from_midi(midi_path, self.tenant_id)
        
        # Should be able to serialize and deserialize
        json_str = json.dumps(result)
        parsed_result = json.loads(json_str)
        
        self.assertEqual(result, parsed_result)
    
    def test_note_timing_relative_to_bar(self):
        """Test that note timings are relative to bar start."""
        midi_path = self._create_synthetic_midi(bars=2, tempo=120.0)
        result = extract_bars_from_midi(midi_path, self.tenant_id)
        
        # Check that notes in each bar start from 0.0
        for bar in result["bars"]:
            if bar["notes"]:
                min_start_time = min(note["start"] for note in bar["notes"])
                self.assertGreaterEqual(min_start_time, 0.0)
                self.assertLess(min_start_time, 2.1)  # Should be within bar duration


if __name__ == "__main__":
    unittest.main()