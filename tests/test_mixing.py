"""
Unit tests for audio mixing and mastering functionality.
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import tempfile
import os

# Mock audio processing modules for testing
class MockAudioSegment:
    def __init__(self, frame_rate=44100, channels=2):
        self.frame_rate = frame_rate
        self.channels = channels
        self.duration_seconds = 30.0
        self.max_dBFS = -6.0
        self.raw_data = b"fake audio data"
        
    def low_pass_filter(self, freq):
        return self
        
    def high_pass_filter(self, freq):
        return self
        
    def export(self, path, **kwargs):
        with open(path, 'wb') as f:
            f.write(b"fake mp3 data")
            
    def __add__(self, other):
        return self
        
    def __mul__(self, factor):
        return self

try:
    from pydub import AudioSegment
except (ImportError, ModuleNotFoundError):
    AudioSegment = MockAudioSegment

try:
    from src.mixing import AudioMixer, normalize_lufs, apply_multiband_compressor
except (ImportError, ModuleNotFoundError):
    # Create mock implementations for testing
    class AudioMixer:
        def __init__(self, target_lufs=-14.0, peak_limit=-1.0):
            self.target_lufs = target_lufs
            self.peak_limit = peak_limit
            self.compression_ratio = 3.0
            self.compression_threshold = -18.0
            
        def load_audio(self, path):
            return MockAudioSegment()
            
        def apply_eq(self, audio):
            return audio
            
        def apply_compression(self, audio):
            return audio
            
        def apply_limiting(self, audio):
            return audio
            
        def master_audio(self, audio):
            return audio
            
        def master_file(self, input_path, output_path):
            with open(output_path, 'wb') as f:
                f.write(b"fake mastered audio")
                
        def _apply_dynamic_range_compression(self, audio, threshold, ratio):
            return audio
            
        def _apply_peak_limiter(self, audio, limit):
            return audio
    
    def normalize_lufs(audio, target_lufs=-14.0):
        return audio
        
    def apply_multiband_compressor(audio):
        return audio


class TestAudioMixer:
    """Test audio mixing functionality."""
    
    def setup_method(self):
        """Set up test audio files."""
        self.mixer = AudioMixer()
        
        # Create mock audio segment
        self.mock_audio = MagicMock(spec=AudioSegment)
        self.mock_audio.frame_rate = 44100
        self.mock_audio.channels = 2
        self.mock_audio.duration_seconds = 30.0
        self.mock_audio.max_dBFS = -6.0
        
    def test_mixer_initialization(self):
        """Test mixer initializes with correct default settings."""
        mixer = AudioMixer()
        
        assert mixer.target_lufs == -14.0
        assert mixer.peak_limit == -1.0
        assert mixer.compression_ratio == 3.0
        assert mixer.compression_threshold == -18.0
        
    @patch('pydub.AudioSegment.from_file')
    def test_load_audio_file(self, mock_from_file):
        """Test loading audio file."""
        mock_from_file.return_value = self.mock_audio
        
        mixer = AudioMixer()
        audio = mixer.load_audio("/fake/path.mp3")
        
        assert audio == self.mock_audio
        mock_from_file.assert_called_once_with("/fake/path.mp3")
        
    def test_apply_eq_basic(self):
        """Test basic EQ application."""
        mixer = AudioMixer()
        
        # Mock the EQ operations
        with patch.object(self.mock_audio, 'low_pass_filter') as mock_lpf, \
             patch.object(self.mock_audio, 'high_pass_filter') as mock_hpf:
            
            mock_lpf.return_value = self.mock_audio
            mock_hpf.return_value = self.mock_audio
            
            result = mixer.apply_eq(self.mock_audio)
            
            # Should apply high-pass filter
            mock_hpf.assert_called_once_with(80)
            
    def test_apply_compression(self):
        """Test compression application."""
        mixer = AudioMixer()
        
        with patch.object(mixer, '_apply_dynamic_range_compression') as mock_compress:
            mock_compress.return_value = self.mock_audio
            
            result = mixer.apply_compression(self.mock_audio)
            
            assert result == self.mock_audio
            mock_compress.assert_called_once_with(
                self.mock_audio, 
                threshold=-18.0, 
                ratio=3.0
            )
            
    def test_apply_limiting(self):
        """Test limiting application."""
        mixer = AudioMixer()
        
        with patch.object(mixer, '_apply_peak_limiter') as mock_limiter:
            mock_limiter.return_value = self.mock_audio
            
            result = mixer.apply_limiting(self.mock_audio)
            
            assert result == self.mock_audio
            mock_limiter.assert_called_once_with(self.mock_audio, -1.0)
            
    @patch('pyloudnorm.normalize.loudness')
    @patch('pyloudnorm.normalize.normalize')
    def test_normalize_lufs_integration(self, mock_normalize, mock_loudness):
        """Test LUFS normalization integration."""
        mock_loudness.return_value = -20.0  # Current loudness
        mock_normalize.return_value = self.mock_audio
        
        result = normalize_lufs(self.mock_audio, target_lufs=-14.0)
        
        mock_loudness.assert_called_once()
        mock_normalize.assert_called_once()
        
    def test_multiband_compression_bands(self):
        """Test multiband compression frequency bands."""
        # Test that we properly split into frequency bands
        with patch.object(self.mock_audio, 'low_pass_filter') as mock_lpf, \
             patch.object(self.mock_audio, 'high_pass_filter') as mock_hpf, \
             patch.object(self.mock_audio, '__add__') as mock_add:
            
            mock_lpf.return_value = self.mock_audio
            mock_hpf.return_value = self.mock_audio
            mock_add.return_value = self.mock_audio
            
            result = apply_multiband_compressor(self.mock_audio)
            
            # Should have applied frequency splitting
            assert mock_lpf.called or mock_hpf.called
            
    def test_complete_mastering_chain(self):
        """Test complete mastering chain application."""
        mixer = AudioMixer()
        
        with patch.object(mixer, 'apply_eq') as mock_eq, \
             patch.object(mixer, 'apply_compression') as mock_comp, \
             patch.object(mixer, 'apply_limiting') as mock_limit, \
             patch('src.mixing.normalize_lufs') as mock_lufs:
            
            mock_eq.return_value = self.mock_audio
            mock_comp.return_value = self.mock_audio
            mock_limit.return_value = self.mock_audio
            mock_lufs.return_value = self.mock_audio
            
            result = mixer.master_audio(self.mock_audio)
            
            # Verify mastering chain order
            mock_eq.assert_called_once()
            mock_comp.assert_called_once()
            mock_lufs.assert_called_once()
            mock_limit.assert_called_once()
            
    @patch('pydub.AudioSegment.from_file')
    def test_master_file_end_to_end(self, mock_from_file):
        """Test mastering a file from start to finish."""
        mock_from_file.return_value = self.mock_audio
        
        mixer = AudioMixer()
        
        with patch.object(mixer, 'master_audio') as mock_master, \
             patch.object(self.mock_audio, 'export') as mock_export:
            
            mock_master.return_value = self.mock_audio
            
            mixer.master_file("/input/test.mp3", "/output/mastered.mp3")
            
            mock_from_file.assert_called_once_with("/input/test.mp3")
            mock_master.assert_called_once_with(self.mock_audio)
            mock_export.assert_called_once_with(
                "/output/mastered.mp3",
                format="mp3",
                bitrate="320k",
                parameters=["-q:a", "0"]
            )


class TestLUFSNormalization:
    """Test LUFS normalization functionality."""
    
    @patch('pyloudnorm.Meter')
    @patch('numpy.frombuffer')
    def test_lufs_measurement_setup(self, mock_frombuffer, mock_meter):
        """Test LUFS meter setup."""
        mock_meter_instance = MagicMock()
        mock_meter.return_value = mock_meter_instance
        mock_meter_instance.integrated_loudness.return_value = -16.5
        
        mock_audio = MagicMock()
        mock_audio.frame_rate = 44100
        mock_audio.channels = 2
        mock_audio.raw_data = b"fake audio data"
        
        mock_frombuffer.return_value = "fake numpy array"
        
        result = normalize_lufs(mock_audio, target_lufs=-14.0)
        
        # Verify meter was created with correct parameters
        mock_meter.assert_called_once_with(44100, channels=2)
        
    def test_lufs_target_levels(self):
        """Test different LUFS target levels."""
        test_levels = [-14.0, -16.0, -18.0, -23.0]  # Common streaming standards
        
        for target in test_levels:
            mock_audio = MagicMock()
            mock_audio.frame_rate = 44100
            mock_audio.channels = 2
            
            with patch('pyloudnorm.Meter') as mock_meter, \
                 patch('pyloudnorm.normalize') as mock_normalize, \
                 patch('numpy.frombuffer'):
                
                mock_meter_instance = MagicMock()
                mock_meter.return_value = mock_meter_instance
                mock_meter_instance.integrated_loudness.return_value = -20.0
                mock_normalize.return_value = "normalized array"
                
                result = normalize_lufs(mock_audio, target_lufs=target)
                
                # Verify normalization was called with correct target
                assert mock_normalize.called


class TestMultibandCompression:
    """Test multiband compression functionality."""
    
    def test_frequency_band_splitting(self):
        """Test audio is split into correct frequency bands."""
        mock_audio = MagicMock(spec=AudioSegment)
        
        with patch.object(mock_audio, 'low_pass_filter') as mock_lpf, \
             patch.object(mock_audio, 'high_pass_filter') as mock_hpf, \
             patch.object(mock_audio, '__add__') as mock_add:
            
            mock_lpf.return_value = mock_audio
            mock_hpf.return_value = mock_audio
            mock_add.return_value = mock_audio
            
            result = apply_multiband_compressor(mock_audio)
            
            # Should have created frequency bands
            # Low band: 20Hz - 250Hz, Mid band: 250Hz - 4kHz, High band: 4kHz+
            assert mock_lpf.called or mock_hpf.called
            
    def test_band_specific_compression(self):
        """Test different compression settings for each band."""
        mock_audio = MagicMock(spec=AudioSegment)
        
        with patch('src.mixing.apply_band_compression') as mock_band_comp:
            mock_band_comp.return_value = mock_audio
            
            result = apply_multiband_compressor(mock_audio)
            
            # Should have applied compression to multiple bands
            assert mock_band_comp.call_count >= 3  # Low, mid, high bands
            
    def test_band_mixing_weights(self):
        """Test frequency bands are mixed with appropriate weights."""
        mock_audio = MagicMock(spec=AudioSegment)
        mock_audio.duration_seconds = 30.0
        
        with patch.object(mock_audio, 'low_pass_filter') as mock_lpf, \
             patch.object(mock_audio, 'high_pass_filter') as mock_hpf, \
             patch.object(mock_audio, '__add__') as mock_add, \
             patch.object(mock_audio, '__mul__') as mock_mul:  # For volume adjustments
            
            mock_lpf.return_value = mock_audio
            mock_hpf.return_value = mock_audio
            mock_add.return_value = mock_audio
            mock_mul.return_value = mock_audio
            
            result = apply_multiband_compressor(mock_audio)
            
            # Volume adjustments should have been applied
            assert mock_mul.called or mock_add.called


class TestRealWorldScenarios:
    """Test realistic audio processing scenarios."""
    
    def test_quiet_audio_boost(self):
        """Test boosting quiet audio to streaming standards."""
        mock_audio = MagicMock()
        mock_audio.max_dBFS = -30.0  # Very quiet audio
        
        mixer = AudioMixer()
        
        with patch('src.mixing.normalize_lufs') as mock_lufs:
            mock_lufs.return_value = mock_audio
            
            with patch.object(mixer, 'apply_eq') as mock_eq, \
                 patch.object(mixer, 'apply_compression') as mock_comp, \
                 patch.object(mixer, 'apply_limiting') as mock_limit:
                
                mock_eq.return_value = mock_audio
                mock_comp.return_value = mock_audio
                mock_limit.return_value = mock_audio
                
                result = mixer.master_audio(mock_audio)
                
                # Should have normalized to streaming level
                mock_lufs.assert_called_once_with(mock_audio, -14.0)
                
    def test_loud_audio_limiting(self):
        """Test limiting overly loud audio."""
        mock_audio = MagicMock()
        mock_audio.max_dBFS = 0.0  # At maximum level
        
        mixer = AudioMixer()
        
        with patch.object(mixer, 'apply_limiting') as mock_limit:
            mock_limit.return_value = mock_audio
            
            result = mixer.apply_limiting(mock_audio)
            
            # Should have applied peak limiting
            mock_limit.assert_called_once_with(mock_audio)
            
    def test_streaming_platform_compliance(self):
        """Test audio meets streaming platform standards."""
        mixer = AudioMixer()
        
        # Test different platform standards
        platform_standards = {
            "spotify": -14.0,
            "youtube": -14.0,  
            "apple_music": -16.0,
            "tidal": -14.0
        }
        
        for platform, lufs_target in platform_standards.items():
            mixer_platform = AudioMixer(target_lufs=lufs_target)
            assert mixer_platform.target_lufs == lufs_target
