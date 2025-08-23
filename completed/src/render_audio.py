"""
Audio rendering module for SERP Loop Radio.
Converts MIDI files to WAV/MP3 using FluidSynth and handles audio processing.
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import json

from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range

logger = logging.getLogger(__name__)


class AudioRenderer:
    """Main class for rendering MIDI to audio formats."""
    
    def __init__(self, config_path: Path = None):
        """Initialize audio renderer with configuration."""
        self.config = self._load_config(config_path)
        self.audio_config = self.config.get("audio", {})
        self.tts_config = self.config.get("tts", {})
        
        # Audio settings
        self.sample_rate = 44100
        self.bit_depth = 16
        self.channels = 2
        
        # Check for FluidSynth
        self._check_fluidsynth()
        
        # Set default soundfont
        self.soundfont_path = self._get_soundfont_path()
        
        logger.info("Audio renderer initialized")
    
    def _load_config(self, config_path: Path) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        if config_path and config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load config: {e}")
        
        # Default configuration
        return {
            "audio": {
                "tempo": 112,
                "soundfont": "assets/nice_gm.sf2"
            },
            "tts": {
                "enabled": False,
                "provider": "openai",
                "voice": "alloy",
                "overlay_volume": 0.3
            }
        }
    
    def _check_fluidsynth(self) -> None:
        """Check if FluidSynth is available."""
        if not shutil.which("fluidsynth"):
            raise RuntimeError(
                "FluidSynth not found. Please install:\n"
                "- macOS: brew install fluidsynth\n"
                "- Ubuntu: sudo apt-get install fluidsynth\n"
                "- Windows: Download from http://www.fluidsynth.org/"
            )
    
    def _get_soundfont_path(self) -> Path:
        """Get path to soundfont file."""
        # Try config path first
        config_sf = self.audio_config.get("soundfont", "")
        if config_sf and Path(config_sf).exists():
            return Path(config_sf)
        
        # Try common locations
        common_paths = [
            Path("assets/nice_gm.sf2"),
            Path("docker/assets/nice_gm.sf2"),
            Path("/usr/share/sounds/sf2/FluidR3_GM.sf2"),  # Ubuntu
            Path("/System/Library/Components/CoreAudio.component/Contents/Resources/gs_instruments.dls"),  # macOS
        ]
        
        for path in common_paths:
            if path.exists():
                logger.info(f"Using soundfont: {path}")
                return path
        
        # If no soundfont found, create a minimal one or use built-in
        logger.warning("No soundfont found, audio quality may be reduced")
        return None
    
    def midi_to_wav(
        self, 
        midi_path: Path, 
        output_path: Path,
        tempo: Optional[int] = None
    ) -> Path:
        """
        Convert MIDI file to WAV using FluidSynth.
        
        Args:
            midi_path: Input MIDI file path
            output_path: Output WAV file path
            tempo: Optional tempo override
            
        Returns:
            Path to created WAV file
        """
        logger.info(f"Converting MIDI to WAV: {midi_path} -> {output_path}")
        
        if not midi_path.exists():
            raise FileNotFoundError(f"MIDI file not found: {midi_path}")
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build FluidSynth command
        cmd = [
            "fluidsynth",
            "-ni",  # No interactive mode
            "-g", "0.5",  # Gain
            "-r", str(self.sample_rate),  # Sample rate
            "-F", str(output_path),  # Output file
        ]
        
        # Add soundfont if available
        if self.soundfont_path:
            cmd.append(str(self.soundfont_path))
        
        # Add MIDI file
        cmd.append(str(midi_path))
        
        try:
            # Run FluidSynth
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                logger.error(f"FluidSynth error: {result.stderr}")
                raise RuntimeError(f"FluidSynth failed: {result.stderr}")
            
            logger.info(f"Successfully created WAV file: {output_path}")
            return output_path
            
        except subprocess.TimeoutExpired:
            logger.error("FluidSynth process timed out")
            raise RuntimeError("Audio rendering timed out")
        except Exception as e:
            logger.error(f"Error running FluidSynth: {e}")
            raise
    
    def wav_to_mp3(
        self, 
        wav_path: Path, 
        mp3_path: Path,
        bitrate: str = "192k"
    ) -> Path:
        """
        Convert WAV to MP3 with compression and normalization.
        
        Args:
            wav_path: Input WAV file path
            mp3_path: Output MP3 file path
            bitrate: MP3 bitrate (e.g., "192k", "320k")
            
        Returns:
            Path to created MP3 file
        """
        logger.info(f"Converting WAV to MP3: {wav_path} -> {mp3_path}")
        
        try:
            # Load audio file
            audio = AudioSegment.from_wav(str(wav_path))
            
            # Audio processing
            # Normalize audio levels
            audio = normalize(audio)
            
            # Apply light compression to even out dynamics
            audio = compress_dynamic_range(audio, threshold=-20.0, ratio=4.0)
            
            # Ensure stereo
            if audio.channels == 1:
                audio = audio.set_channels(2)
            
            # Export as MP3
            mp3_path.parent.mkdir(parents=True, exist_ok=True)
            audio.export(
                str(mp3_path),
                format="mp3",
                bitrate=bitrate,
                tags={
                    "title": "SERP Loop Radio Daily Report",
                    "artist": "SERP Loop Radio",
                    "album": "Daily Analytics",
                    "genre": "Data Sonification"
                }
            )
            
            logger.info(f"Successfully created MP3 file: {mp3_path}")
            return mp3_path
            
        except Exception as e:
            logger.error(f"Error converting to MP3: {e}")
            raise
    
    def midi_to_mp3(
        self, 
        midi_path: Path, 
        mp3_path: Path,
        tempo: Optional[int] = None,
        add_tts: bool = False
    ) -> Path:
        """
        Convert MIDI directly to MP3 (convenience method).
        
        Args:
            midi_path: Input MIDI file
            mp3_path: Output MP3 file
            tempo: Optional tempo override
            add_tts: Whether to add TTS overlay
            
        Returns:
            Path to created MP3 file
        """
        # Create temporary WAV file
        temp_wav = mp3_path.with_suffix('.wav')
        
        try:
            # Convert to WAV
            self.midi_to_wav(midi_path, temp_wav, tempo)
            
            # Add TTS overlay if requested
            if add_tts and self.tts_config.get("enabled", False):
                temp_wav = self._add_tts_overlay(temp_wav)
            
            # Convert to MP3
            result = self.wav_to_mp3(temp_wav, mp3_path)
            
            return result
            
        finally:
            # Clean up temporary WAV file
            if temp_wav.exists():
                temp_wav.unlink()
    
    def _add_tts_overlay(self, wav_path: Path) -> Path:
        """Add text-to-speech overlay to audio file."""
        # This is a placeholder for TTS integration
        # In production, would integrate with OpenAI TTS or AWS Polly
        
        logger.info("TTS overlay requested but not implemented in MVP")
        
        # For MVP, just return the original file
        return wav_path
    
    def create_summary_audio(
        self, 
        midi_path: Path, 
        output_path: Path,
        summary_text: Optional[str] = None
    ) -> Path:
        """
        Create a complete audio summary with optional narration.
        
        Args:
            midi_path: Input MIDI file
            output_path: Output audio file
            summary_text: Optional text for TTS narration
            
        Returns:
            Path to created audio file
        """
        logger.info("Creating audio summary")
        
        # Convert MIDI to audio
        if output_path.suffix.lower() == '.mp3':
            result_path = self.midi_to_mp3(midi_path, output_path)
        else:
            result_path = self.midi_to_wav(midi_path, output_path)
        
        # Add intro/outro sounds (placeholder for future enhancement)
        # This could include brand jingles, intro music, etc.
        
        return result_path
    
    def get_audio_info(self, audio_path: Path) -> Dict[str, Any]:
        """Get information about an audio file."""
        try:
            audio = AudioSegment.from_file(str(audio_path))
            
            return {
                "duration": len(audio) / 1000.0,  # Duration in seconds
                "channels": audio.channels,
                "frame_rate": audio.frame_rate,
                "sample_width": audio.sample_width,
                "max_dBFS": audio.max_dBFS,
                "file_size": audio_path.stat().st_size
            }
        except Exception as e:
            logger.error(f"Could not get audio info: {e}")
            return {}


def midi_to_wav(
    midi_path: Path, 
    wav_path: Path, 
    soundfont_path: Optional[Path] = None,
    tempo: int = 112
) -> Path:
    """
    Convenience function to convert MIDI to WAV.
    
    Args:
        midi_path: Input MIDI file
        wav_path: Output WAV file
        soundfont_path: Optional soundfont file
        tempo: Tempo in BPM
        
    Returns:
        Path to created WAV file
    """
    renderer = AudioRenderer()
    if soundfont_path:
        renderer.soundfont_path = soundfont_path
    
    return renderer.midi_to_wav(midi_path, wav_path, tempo)


def check_audio_dependencies() -> Dict[str, bool]:
    """Check if required audio tools are available."""
    dependencies = {
        "fluidsynth": bool(shutil.which("fluidsynth")),
        "ffmpeg": bool(shutil.which("ffmpeg")),
    }
    
    return dependencies


if __name__ == "__main__":
    # Test audio rendering
    renderer = AudioRenderer()
    
    # Check dependencies
    deps = check_audio_dependencies()
    print("Audio dependencies:", deps)
    
    # Test with sample MIDI file if available
    test_midi = Path("/tmp/test_serp.mid")
    if test_midi.exists():
        test_wav = Path("/tmp/test_serp.wav")
        test_mp3 = Path("/tmp/test_serp.mp3")
        
        try:
            # Test WAV conversion
            renderer.midi_to_wav(test_midi, test_wav)
            print(f"Created WAV: {test_wav}")
            
            # Test MP3 conversion
            renderer.wav_to_mp3(test_wav, test_mp3)
            print(f"Created MP3: {test_mp3}")
            
            # Get audio info
            info = renderer.get_audio_info(test_mp3)
            print("Audio info:", info)
            
        except Exception as e:
            print(f"Audio rendering test failed: {e}")
    else:
        print("No test MIDI file found. Run sonify.py first to create one.") 