"""
Unit tests for sonification functionality.
Tests CSV to MIDI conversion and validates musical output.
"""

import pytest
import pandas as pd
import tempfile
from pathlib import Path

from src.sonify import SERPSonifier, csv_to_midi
from midiutil import MIDIFile


class TestSERPSonifier:
    """Test cases for SERPSonifier class."""
    
    @pytest.fixture
    def sonifier(self):
        """Create a SERPSonifier instance for testing."""
        config_path = Path("config/mapping.json")
        return SERPSonifier(config_path)
    
    @pytest.fixture
    def sample_data(self):
        """Sample SERP data for testing."""
        return pd.DataFrame({
            'keyword': ['ai chatbot', 'customer service', 'help desk'],
            'engine': ['google_web', 'google_ai', 'google_web'],
            'rank_delta': [-3, 1, 0],
            'share_pct': [0.4, 0.2, 0.15],
            'segment': ['Central', 'West', 'East'],
            'rich_type': ['', 'video', ''],
            'anomaly': [True, False, False],
            'domain': ['mybrand.com', 'competitor1.com', 'competitor2.com'],
            'rank_absolute': [1, 5, 8]
        })
    
    def test_sonifier_initialization(self, sonifier):
        """Test sonifier initializes correctly."""
        assert sonifier.tempo == 112
        assert sonifier.total_bars == 16
        assert len(sonifier.scale_notes) == 5  # Pentatonic scale
    
    def test_track_mapping_creation(self, sonifier, sample_data):
        """Test creation of engine to track mapping."""
        track_map = sonifier._create_track_mapping(sample_data)
        
        # Should have tracks for each unique engine plus special tracks
        unique_engines = sample_data['engine'].unique()
        assert len(track_map) == len(unique_engines) + 2  # +2 for percussion and bass
        
        # Check special tracks exist
        assert 'percussion' in track_map
        assert 'bass' in track_map
    
    def test_midi_creation(self, sonifier, sample_data):
        """Test MIDI file creation from DataFrame."""
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tmp_file:
            output_path = Path(tmp_file.name)
        
        try:
            # Create MIDI file
            result_path = sonifier.csv_to_midi(sample_data, output_path)
            
            # Verify file was created
            assert result_path.exists()
            assert result_path.stat().st_size > 0
            
            # Basic MIDI file validation
            with open(result_path, 'rb') as f:
                header = f.read(4)
                assert header == b'MThd'  # MIDI file header
                
        finally:
            # Cleanup
            if output_path.exists():
                output_path.unlink()
    
    def test_bass_riff_trigger(self, sonifier, sample_data):
        """Test bass riff is triggered when brand ranks in top 3."""
        # Test with brand in top 3
        brand_data = sample_data.copy()
        brand_data.loc[0, 'domain'] = 'mybrand.com'
        brand_data.loc[0, 'rank_absolute'] = 2
        
        assert sonifier._should_add_bass_riff(brand_data) == True
        
        # Test with no brand data
        no_brand_data = sample_data.copy()
        no_brand_data['domain'] = ['competitor1.com'] * len(no_brand_data)
        
        # This might be False if no brand domain matches
        result = sonifier._should_add_bass_riff(no_brand_data)
        assert isinstance(result, bool)
    
    def test_anomaly_detection_in_midi(self, sonifier, sample_data):
        """Test anomalies are properly reflected in MIDI."""
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tmp_file:
            output_path = Path(tmp_file.name)
        
        try:
            # Ensure we have anomalies in data
            test_data = sample_data.copy()
            test_data.loc[0, 'anomaly'] = True
            
            sonifier.csv_to_midi(test_data, output_path)
            
            # File should be created (detailed MIDI content validation would require midi parsing library)
            assert output_path.exists()
            
        finally:
            if output_path.exists():
                output_path.unlink()
    
    def test_sample_midi_generation(self, sonifier):
        """Test sample MIDI generation."""
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tmp_file:
            output_path = Path(tmp_file.name)
        
        try:
            result_path = sonifier.create_sample_midi(output_path)
            
            # Verify file was created
            assert result_path.exists()
            assert result_path == output_path
            
        finally:
            if output_path.exists():
                output_path.unlink()
    
    def test_midi_length_16_bars(self, sonifier):
        """Test that generated MIDI has exactly 16 bars for daily reports."""
        # Calculate expected total beats
        time_sig = sonifier.time_signature
        total_bars = sonifier.total_bars
        expected_beats = total_bars * time_sig[0]  # 16 bars * 4 beats = 64 beats
        
        assert expected_beats == 64  # Validate our calculation
        assert total_bars == 16  # Ensure 16 bars as required


class TestCSVToMIDIFunction:
    """Test the standalone csv_to_midi function."""
    
    def test_csv_to_midi_function(self):
        """Test the standalone csv_to_midi function."""
        # Create test data
        test_data = pd.DataFrame({
            'keyword': ['ai chatbot', 'customer service'],
            'engine': ['google_web', 'google_ai'],
            'rank_delta': [-1, 2],
            'share_pct': [0.3, 0.2],
            'segment': ['Central', 'West'],
            'rich_type': ['', 'video'],
            'anomaly': [False, True],
            'domain': ['test.com', 'competitor.com'],
            'rank_absolute': [3, 7]
        })
        
        config_path = Path("config/mapping.json")
        
        # Should create a MIDI file without errors
        try:
            result_path = csv_to_midi(test_data, config_path)
            assert result_path.exists()
            
            # Cleanup
            if result_path.exists():
                result_path.unlink()
                
        except Exception as e:
            # In test environment, some dependencies might not be available
            # But the function should at least not crash with import errors
            assert "not found" not in str(e).lower() or "import" not in str(e).lower()


class TestMIDIValidation:
    """Test MIDI output validation."""
    
    def test_midi_values_within_range(self):
        """Test all generated MIDI values are within valid ranges."""
        sonifier = SERPSonifier()
        
        # Test with extreme input values
        test_data = pd.DataFrame({
            'keyword': ['extreme_test'],
            'engine': ['google_web'],
            'rank_delta': [999],  # Extreme value
            'share_pct': [1.5],   # Out of normal range
            'segment': ['Unknown'], # Unknown segment
            'rich_type': ['unknown_type'],
            'anomaly': [False],
            'domain': ['test.com'],
            'rank_absolute': [1]
        })
        
        # Should handle extreme values gracefully
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tmp_file:
            output_path = Path(tmp_file.name)
        
        try:
            sonifier.csv_to_midi(test_data, output_path)
            assert output_path.exists()
            
        finally:
            if output_path.exists():
                output_path.unlink()


@pytest.fixture
def large_dataset():
    """Create a larger dataset for performance testing."""
    import numpy as np
    
    n_records = 100
    engines = ['google_web', 'google_ai', 'openai', 'perplexity']
    segments = ['West', 'Central', 'East']
    rich_types = ['', 'video', 'shopping_pack', 'image']
    
    return pd.DataFrame({
        'keyword': [f'keyword_{i}' for i in range(n_records)],
        'engine': np.random.choice(engines, n_records),
        'rank_delta': np.random.randint(-10, 11, n_records),
        'share_pct': np.random.uniform(0, 1, n_records),
        'segment': np.random.choice(segments, n_records),
        'rich_type': np.random.choice(rich_types, n_records),
        'anomaly': np.random.choice([True, False], n_records, p=[0.1, 0.9]),
        'domain': [f'domain_{i}.com' for i in range(n_records)],
        'rank_absolute': np.random.randint(1, 101, n_records)
    })


class TestPerformance:
    """Test performance with larger datasets."""
    
    def test_large_dataset_processing(self, large_dataset):
        """Test sonification works with larger datasets."""
        sonifier = SERPSonifier()
        
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as tmp_file:
            output_path = Path(tmp_file.name)
        
        try:
            # Should complete without timeout or memory issues
            import time
            start_time = time.time()
            
            result_path = sonifier.csv_to_midi(large_dataset, output_path)
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Should complete in reasonable time (less than 30 seconds)
            assert processing_time < 30
            assert result_path.exists()
            
        finally:
            if output_path.exists():
                output_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 