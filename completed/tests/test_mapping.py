"""
Unit tests for musical mapping functionality.
Tests FATLD mapping logic and MIDI value validation.
"""

import pytest
import pandas as pd
from pathlib import Path

from src.mappings import MusicMappings, validate_midi_values, load_mappings


class TestMusicMappings:
    """Test cases for MusicMappings class."""
    
    def test_pitch_mapping_range(self):
        """Test rank delta to pitch mapping stays within bounds."""
        mappings = MusicMappings()
        
        # Test extreme values
        assert -12 <= mappings.get_pitch_from_rank_delta(-10) <= 12
        assert -12 <= mappings.get_pitch_from_rank_delta(10) <= 12
        assert mappings.get_pitch_from_rank_delta(0) == 0
    
    def test_velocity_mapping(self):
        """Test share percentage to velocity mapping."""
        mappings = MusicMappings()
        
        # Test range boundaries
        vel_min = mappings.get_velocity_from_share(0.0)
        vel_max = mappings.get_velocity_from_share(1.0)
        
        assert 40 <= vel_min <= 127
        assert 40 <= vel_max <= 127
        assert vel_max > vel_min
    
    def test_instrument_mapping(self):
        """Test engine to instrument mapping."""
        mappings = MusicMappings()
        
        # Test known mappings
        assert mappings.get_instrument_from_engine("google_web") == 0
        assert mappings.get_instrument_from_engine("unknown_engine") == 0  # Default
    
    def test_scale_generation(self):
        """Test musical scale generation."""
        mappings = MusicMappings()
        
        # Test C pentatonic scale
        c_pentatonic = mappings.get_scale_notes("C", "pentatonic")
        assert len(c_pentatonic) == 5
        assert 60 in c_pentatonic  # Middle C should be in the scale
        
        # Test all notes are valid MIDI numbers
        for note in c_pentatonic:
            assert 0 <= note <= 127
    
    def test_fit_to_scale(self):
        """Test fitting notes to musical scales."""
        mappings = MusicMappings()
        scale_notes = [60, 62, 64, 67, 69]  # C pentatonic
        
        # Test exact match
        assert mappings.fit_to_scale(60, scale_notes) == 60
        
        # Test closest note selection
        fitted = mappings.fit_to_scale(61, scale_notes)
        assert fitted in scale_notes
    
    def test_quantize_to_grid(self):
        """Test timing quantization to musical grid."""
        mappings = MusicMappings()
        
        # Test 16th note quantization
        assert mappings.quantize_to_grid(0.1, 0.25) == 0.0
        assert mappings.quantize_to_grid(0.2, 0.25) == 0.25
        assert mappings.quantize_to_grid(1.1, 0.25) == 1.0


class TestMIDIValidation:
    """Test MIDI value validation functions."""
    
    def test_validate_midi_values(self):
        """Test MIDI value clamping to legal ranges."""
        # Test normal values
        note, vel, chan = validate_midi_values(60, 100, 0)
        assert note == 60
        assert vel == 100
        assert chan == 0
        
        # Test clamping high values
        note, vel, chan = validate_midi_values(200, 200, 20)
        assert note == 127
        assert vel == 127
        assert chan == 15
        
        # Test clamping low values
        note, vel, chan = validate_midi_values(-10, -10, -5)
        assert note == 0
        assert vel == 0
        assert chan == 0


class TestConfigLoading:
    """Test configuration loading functionality."""
    
    def test_load_mappings_default(self):
        """Test loading mappings with default config."""
        mappings = load_mappings()
        assert isinstance(mappings, MusicMappings)
    
    def test_load_mappings_with_config(self):
        """Test loading mappings with specific config file."""
        # Test with existing config
        config_path = Path("config/mapping.json")
        if config_path.exists():
            mappings = load_mappings(config_path)
            assert isinstance(mappings, MusicMappings)
            assert mappings.config is not None


@pytest.fixture
def sample_serp_data():
    """Sample SERP data for testing."""
    return pd.DataFrame({
        'keyword': ['ai chatbot', 'customer service', 'help desk'],
        'engine': ['google_web', 'google_ai', 'google_web'],
        'rank_delta': [-2, 1, 0],
        'share_pct': [0.3, 0.1, 0.2],
        'segment': ['Central', 'West', 'East'],
        'rich_type': ['', 'video', 'shopping_pack'],
        'anomaly': [False, True, False],
        'domain': ['openai.com', 'intercom.com', 'zendesk.com']
    })


class TestIntegration:
    """Integration tests for mapping with real data."""
    
    def test_mapping_with_sample_data(self, sample_serp_data):
        """Test mappings work with sample SERP data."""
        mappings = MusicMappings()
        
        for _, row in sample_serp_data.iterrows():
            # Test all mapping functions work without errors
            pitch = mappings.get_pitch_from_rank_delta(row['rank_delta'])
            velocity = mappings.get_velocity_from_share(row['share_pct'])
            instrument = mappings.get_instrument_from_engine(row['engine'])
            pan = mappings.get_pan_from_segment(row['segment'])
            duration = mappings.get_duration_from_rich_type(row['rich_type'])
            
            # Validate all values are reasonable
            assert -12 <= pitch <= 12
            assert 0 <= velocity <= 127
            assert 0 <= instrument <= 127
            assert -100 <= pan <= 100
            assert 0 < duration <= 2.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 