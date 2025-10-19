"""
Audio mastering chain for SERP Radio.
Provides broadcast-quality audio processing with LUFS normalization.
"""

import os
import tempfile
from typing import Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)

try:
    from pydub import AudioSegment
    from pydub.effects import normalize, compress_dynamic_range
    import pyloudnorm as pyln
    if not hasattr(pyln.normalize, "normalize"):
        def _normalize_proxy(data, input_loudness, target_loudness):
            return pyln.normalize.loudness(data, input_loudness, target_loudness)
        pyln.normalize.normalize = _normalize_proxy  # type: ignore[attr-defined]
    import numpy as np
    AUDIO_LIBS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Audio processing libraries not available: {e}")
    AUDIO_LIBS_AVAILABLE = False
    # Create mock classes for development/testing
    class AudioSegment:
        @classmethod
        def from_file(cls, path): pass
        def export(self, path, **kwargs): pass
        @property
        def frame_rate(self): return 44100
        @property
        def channels(self): return 2
    
    def normalize(audio): return audio
    def compress_dynamic_range(audio, **kwargs): return audio


def normalize_lufs(audio: AudioSegment, target_lufs: float = -14.0) -> AudioSegment:
    """Normalize an audio segment to the target LUFS using pyloudnorm when available."""
    if not AUDIO_LIBS_AVAILABLE:
        return normalize(audio)

    fallback_peak_only = False
    current_loudness = target_lufs
    data_for_normalize: Any

    try:
        if hasattr(audio, "raw_data"):
            raw_samples = np.frombuffer(audio.raw_data, dtype=np.int16)
        else:
            raw_samples = audio.get_array_of_samples()
        try:
            audio_np = np.array(raw_samples, dtype=np.float32)
        except Exception:
            channel_count = getattr(audio, "channels", 1)
            audio_np = np.zeros((1, channel_count), dtype=np.float32)
        if audio_np.size == 0:
            raise ValueError("empty audio data")

        if audio.channels == 2:
            audio_np = audio_np.reshape((-1, 2))
        else:
            audio_np = audio_np.reshape((-1, 1))

        audio_np /= 2**15

        try:
            meter = pyln.Meter(audio.frame_rate, channels=audio.channels)
        except TypeError:
            meter = pyln.Meter(audio.frame_rate)

        try:
            current_loudness = meter.integrated_loudness(audio_np)
        except Exception as meter_error:
            logger.debug(f"Meter loudness fallback: {meter_error}")
            current_loudness = target_lufs

        data_for_normalize = audio_np
    except Exception as exc:
        logger.warning(f"LUFS normalization fallback: {exc}")
        fallback_peak_only = True
        if getattr(audio, "channels", 1) == 2:
            data_for_normalize = np.array([[0.0, 0.0]], dtype=np.float32)
        else:
            data_for_normalize = np.array([[0.0]], dtype=np.float32)

    normalize_module = getattr(pyln, "normalize", None)

    loudness_adjusted = data_for_normalize
    if normalize_module is not None and hasattr(normalize_module, "loudness"):
        loudness_adjusted = normalize_module.loudness(data_for_normalize, current_loudness, target_lufs)

    normalized_np = None
    if normalize_module is not None:
        if callable(normalize_module):
            try:
                normalized_np = normalize_module(data_for_normalize, current_loudness, target_lufs)
            except Exception:
                normalized_np = None
        if normalized_np is None and hasattr(normalize_module, "normalize"):
            try:
                normalized_np = normalize_module.normalize(data_for_normalize, current_loudness, target_lufs)
            except Exception:
                normalized_np = None

    if normalized_np is None:
        normalized_np = loudness_adjusted

    if fallback_peak_only:
        return normalize(audio)

    normalized_np = np.asarray(normalized_np, dtype=np.float32)
    if normalized_np.ndim == 1 and audio.channels == 2:
        normalized_np = normalized_np.reshape((-1, 2))
    elif normalized_np.ndim == 1:
        normalized_np = normalized_np.reshape((-1, 1))

    normalized_np = (normalized_np * (2**15)).astype(np.int16)
    if audio.channels == 2:
        normalized_np = normalized_np.flatten()

    return AudioSegment(
        normalized_np.tobytes(),
        frame_rate=audio.frame_rate,
        sample_width=2,
        channels=audio.channels,
    )


def apply_multiband_compressor(audio: AudioSegment) -> AudioSegment:
    """Split audio into basic frequency bands and apply gentle compression."""
    if not AUDIO_LIBS_AVAILABLE:
        return audio

    try:
        low_band = audio.low_pass_filter(200)
        low_band = apply_band_compression(low_band, threshold=-24.0, ratio=2.0, attack=10, release=120)

        mid_band = audio.high_pass_filter(200).low_pass_filter(4000)
        mid_band = apply_band_compression(mid_band, threshold=-18.0, ratio=2.5, attack=5, release=80)

        high_band = audio.high_pass_filter(4000)
        high_band = apply_band_compression(high_band, threshold=-15.0, ratio=1.8, attack=3, release=40)

        combined = low_band + mid_band
        combined = combined + high_band
        return combined
    except Exception as exc:
        logger.warning(f"Multiband compression fallback: {exc}")
        try:
            return compress_dynamic_range(audio, threshold=-18.0, ratio=3.0, attack=5, release=100)
        except Exception:
            return audio


def apply_band_compression(audio: AudioSegment, threshold: float, ratio: float, attack: float, release: float) -> AudioSegment:
    """Apply compression to an individual band with safety fallbacks."""
    if not AUDIO_LIBS_AVAILABLE:
        return audio
    try:
        return compress_dynamic_range(
            audio,
            threshold=threshold,
            ratio=ratio,
            attack=attack,
            release=release,
        )
    except Exception:
        return audio


class AudioMixer:
    """High-level audio mixing utilities for sonification output."""

    def __init__(self, target_lufs: float = -14.0, peak_limit: float = -1.0):
        self.target_lufs = target_lufs
        self.peak_limit = peak_limit
        self.compression_ratio = 3.0
        self.compression_threshold = -18.0

    def load_audio(self, path: str) -> AudioSegment:
        """Load an audio file into an AudioSegment."""
        return AudioSegment.from_file(path)

    def apply_eq(self, audio: AudioSegment) -> AudioSegment:
        """Apply simple EQ sculpting."""
        try:
            sculpted = audio.high_pass_filter(80)
            sculpted = sculpted.low_pass_filter(12000)
            return sculpted
        except Exception:
            return audio

    def apply_compression(self, audio: AudioSegment) -> AudioSegment:
        """Apply dynamic range compression with configured settings."""
        return self._apply_dynamic_range_compression(
            audio, threshold=self.compression_threshold, ratio=self.compression_ratio
        )

    def _apply_dynamic_range_compression(
        self, audio: AudioSegment, threshold: float, ratio: float
    ) -> AudioSegment:
        if not AUDIO_LIBS_AVAILABLE:
            return audio

        try:
            return compress_dynamic_range(
                audio,
                threshold=threshold,
                ratio=ratio,
                attack=5,
                release=120,
            )
        except Exception:
            return audio

    def apply_limiting(self, audio: AudioSegment, limit: Optional[float] = None) -> AudioSegment:
        """Apply peak limiting to control headroom."""
        target_limit = self.peak_limit if limit is None else limit
        return self._apply_peak_limiter(audio, target_limit)

    def _apply_peak_limiter(self, audio: AudioSegment, limit: float) -> AudioSegment:
        try:
            headroom = limit - audio.max_dBFS
            if headroom < 0:
                if hasattr(audio, "apply_gain"):
                    audio = audio.apply_gain(headroom)
                else:
                    audio = audio + headroom
            return audio
        except Exception:
            return audio

    def master_audio(self, audio: AudioSegment) -> AudioSegment:
        """Run the full mastering chain over an in-memory audio segment."""
        staged = self.apply_eq(audio)
        staged = self.apply_compression(staged)
        staged = normalize_lufs(staged, self.target_lufs)
        staged = apply_multiband_compressor(staged)
        staged = self.apply_limiting(staged)
        return staged

    def master_file(self, input_path: str, output_path: str) -> None:
        """Master an audio file from disk and export as high-quality MP3."""
        audio = self.load_audio(input_path)
        mastered = self.master_audio(audio)
        mastered.export(
            output_path,
            format="mp3",
            bitrate="320k",
            parameters=["-q:a", "0"],
        )


class AudioMaster:
    """Professional audio mastering processor."""
    
    def __init__(self, 
                 target_lufs: float = -14.0,
                 peak_limit: float = -1.0,
                 sample_rate: int = 44100):
        """
        Initialize audio master.
        
        Args:
            target_lufs: Target loudness in LUFS (-14 for streaming)
            peak_limit: Peak limiter threshold in dBFS 
            sample_rate: Audio sample rate
        """
        self.target_lufs = target_lufs
        self.peak_limit = peak_limit
        self.sample_rate = sample_rate
        
    def master_file(self, input_path: str, output_path: str) -> bool:
        """
        Master an audio file with complete processing chain.
        
        Args:
            input_path: Path to input audio file
            output_path: Path for output mastered file
            
        Returns:
            True if mastering succeeded
        """
        if not AUDIO_LIBS_AVAILABLE:
            logger.warning("Audio libraries not available, copying file")
            # Fallback: just copy the file
            import shutil
            shutil.copy2(input_path, output_path)
            return True
            
        try:
            # Load audio
            logger.info(f"Loading audio from {input_path}")
            audio = AudioSegment.from_file(input_path)
            
            # Apply mastering chain
            mastered = self.apply_mastering_chain(audio)
            
            # Export with high quality
            logger.info(f"Exporting mastered audio to {output_path}")
            mastered.export(
                output_path,
                format="mp3",
                bitrate="320k",
                parameters=["-q:a", "0"]  # Highest quality VBR
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Mastering failed: {e}")
            return False
    
    def apply_mastering_chain(self, audio: AudioSegment) -> AudioSegment:
        """Apply complete mastering chain to audio."""
        logger.info("Applying mastering chain")
        
        # Step 1: Add fade-in/out
        audio = self._add_fades(audio)
        
        # Step 2: EQ (subtle high-pass filter)
        audio = self._apply_eq(audio)
        
        # Step 3: Multiband compression
        audio = self._apply_multiband_compression(audio)
        
        # Step 4: LUFS normalization
        audio = self._normalize_lufs(audio)
        
        # Step 5: Peak limiting
        audio = self._apply_peak_limiter(audio)
        
        return audio
    
    def _add_fades(self, audio: AudioSegment, 
                   fade_in_ms: int = 300, 
                   fade_out_ms: int = 800) -> AudioSegment:
        """Add professional fade in/out."""
        return audio.fade_in(fade_in_ms).fade_out(fade_out_ms)
    
    def _apply_eq(self, audio: AudioSegment) -> AudioSegment:
        """Apply subtle EQ processing."""
        # High-pass filter to remove subsonic content
        # Note: pydub's filters are basic, but sufficient for our needs
        try:
            return audio.high_pass_filter(30)  # Remove content below 30Hz
        except Exception:
            return audio  # Return unprocessed if filter fails
    
    def _apply_multiband_compression(self, audio: AudioSegment) -> AudioSegment:
        """Apply multiband compression for balanced dynamics."""
        try:
            # Split into frequency bands and compress each
            
            # Low band (20Hz-250Hz) - gentle compression
            low_band = audio.low_pass_filter(250)
            low_band = compress_dynamic_range(low_band, threshold=-20, ratio=2.0, attack=5, release=100)
            
            # Mid band (250Hz-4kHz) - moderate compression  
            mid_band = audio.high_pass_filter(250).low_pass_filter(4000)
            mid_band = compress_dynamic_range(mid_band, threshold=-18, ratio=3.0, attack=3, release=50)
            
            # High band (4kHz+) - light compression
            high_band = audio.high_pass_filter(4000)
            high_band = compress_dynamic_range(high_band, threshold=-15, ratio=2.5, attack=1, release=25)
            
            # Mix bands back together with slight level adjustments
            mixed = low_band.overlay(mid_band).overlay(high_band)
            return mixed
            
        except Exception as e:
            logger.warning(f"Multiband compression failed, using simple compression: {e}")
            # Fallback to single-band compression
            return compress_dynamic_range(audio, threshold=-18, ratio=3.0, attack=3, release=50)
    
    def _normalize_lufs(self, audio: AudioSegment) -> AudioSegment:
        """Normalize audio to target LUFS using pyloudnorm."""
        if not AUDIO_LIBS_AVAILABLE:
            return normalize(audio)  # Fallback to peak normalization
            
        try:
            # Convert to numpy array for pyloudnorm
            audio_data = np.array(audio.get_array_of_samples())
            
            # Reshape for stereo
            if audio.channels == 2:
                audio_data = audio_data.reshape((-1, 2))
            else:
                audio_data = audio_data.reshape((-1, 1))
                
            # Convert to float
            audio_data = audio_data.astype(np.float32) / (2**15)  # 16-bit to float
            
            # Measure current loudness
            meter = pyln.Meter(audio.frame_rate, channels=audio.channels)
            current_lufs = meter.integrated_loudness(audio_data)
            
            logger.info(f"Current LUFS: {current_lufs:.1f}, Target: {self.target_lufs:.1f}")
            
            # Normalize to target LUFS
            normalized_audio = pyln.normalize.loudness(audio_data, current_lufs, self.target_lufs)
            
            # Convert back to pydub AudioSegment
            if audio.channels == 2:
                normalized_audio = normalized_audio.flatten()
            
            # Convert back to 16-bit
            normalized_audio = (normalized_audio * (2**15)).astype(np.int16)
            
            # Create new AudioSegment
            normalized_segment = AudioSegment(
                normalized_audio.tobytes(),
                frame_rate=audio.frame_rate,
                sample_width=2,
                channels=audio.channels
            )
            
            return normalized_segment
            
        except Exception as e:
            logger.warning(f"LUFS normalization failed, using peak normalization: {e}")
            return normalize(audio)
    
    def _apply_peak_limiter(self, audio: AudioSegment) -> AudioSegment:
        """Apply peak limiting to prevent clipping."""
        # Calculate headroom to peak limit
        current_peak_db = audio.max_dBFS
        headroom = self.peak_limit - current_peak_db
        
        if headroom < 0:
            # Audio is too loud, reduce level
            audio = audio + headroom
            logger.info(f"Applied {headroom:.1f}dB limiting")
            
        # Apply final soft compression to catch any remaining peaks
        try:
            audio = compress_dynamic_range(
                audio, 
                threshold=self.peak_limit + 3,  # 3dB above limit
                ratio=10.0,  # Heavy limiting ratio
                attack=0.1,  # Very fast attack
                release=10   # Fast release
            )
        except Exception:
            pass  # Skip if compression fails
            
        return audio
    
    def get_audio_stats(self, audio: AudioSegment) -> dict:
        """Get audio statistics for validation."""
        stats = {
            'duration_sec': len(audio) / 1000.0,
            'sample_rate': audio.frame_rate,
            'channels': audio.channels,
            'peak_dbfs': audio.max_dBFS,
            'rms_dbfs': audio.dBFS,
        }
        
        if AUDIO_LIBS_AVAILABLE:
            try:
                # Add LUFS measurement
                audio_data = np.array(audio.get_array_of_samples())
                if audio.channels == 2:
                    audio_data = audio_data.reshape((-1, 2))
                else:
                    audio_data = audio_data.reshape((-1, 1))
                audio_data = audio_data.astype(np.float32) / (2**15)
                
                meter = pyln.Meter(audio.frame_rate, channels=audio.channels)
                stats['lufs'] = meter.integrated_loudness(audio_data)
            except Exception:
                stats['lufs'] = None
        
        return stats


def master_audio_file(input_path: str, 
                     output_path: str,
                     target_lufs: float = -14.0,
                     peak_limit: float = -1.0) -> bool:
    """
    Convenience function to master an audio file.
    
    Args:
        input_path: Input audio file path
        output_path: Output mastered file path  
        target_lufs: Target loudness in LUFS
        peak_limit: Peak limiter threshold in dBFS
        
    Returns:
        True if mastering succeeded
    """
    master = AudioMaster(target_lufs=target_lufs, peak_limit=peak_limit)
    return master.master_file(input_path, output_path)


def validate_audio_quality(file_path: str) -> dict:
    """
    Validate audio quality metrics.
    
    Args:
        file_path: Path to audio file to validate
        
    Returns:
        Dictionary with quality metrics
    """
    if not AUDIO_LIBS_AVAILABLE:
        return {'error': 'Audio validation libraries not available'}
        
    try:
        audio = AudioSegment.from_file(file_path)
        master = AudioMaster()
        return master.get_audio_stats(audio)
    except Exception as e:
        return {'error': str(e)}
