"""
MIDI to MP3 rendering using FluidSynth and FFmpeg.
Gracefully handles missing dependencies for cloud deployment.
"""

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Check for required binaries at import time
FLUIDSYNTH_AVAILABLE = shutil.which("fluidsynth") is not None
FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None
RENDER_ENABLED = os.getenv("RENDER_MP3", "0") == "1"

if RENDER_ENABLED and not (FLUIDSYNTH_AVAILABLE and FFMPEG_AVAILABLE):
    logger.warning(
        f"MP3 rendering requested but missing dependencies: "
        f"fluidsynth={FLUIDSYNTH_AVAILABLE}, ffmpeg={FFMPEG_AVAILABLE}"
    )


def render_midi_to_mp3(midi_bytes: bytes) -> Optional[bytes]:
    """
    Convert MIDI bytes to MP3 using FluidSynth and FFmpeg.
    
    Args:
        midi_bytes: MIDI file data as bytes
    
    Returns:
        MP3 file data as bytes, or None if rendering disabled/failed
    """
    if not RENDER_ENABLED:
        logger.debug("MP3 rendering disabled (RENDER_MP3=0)")
        return None
    
    if not FLUIDSYNTH_AVAILABLE:
        logger.error("FluidSynth not available for MP3 rendering")
        return None
    
    if not FFMPEG_AVAILABLE:
        logger.error("FFmpeg not available for MP3 rendering")
        return None
    
    temp_dir = None
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix="serp_render_")
        
        midi_path = Path(temp_dir) / "input.mid"
        wav_path = Path(temp_dir) / "output.wav"
        mp3_path = Path(temp_dir) / "output.mp3"
        
        # Write MIDI to temp file
        with open(midi_path, "wb") as f:
            f.write(midi_bytes)
        
        # Find soundfont (prioritize local, fallback to system)
        soundfont_path = _find_soundfont()
        if not soundfont_path:
            logger.error("No soundfont found for MP3 rendering")
            return None
        
        # Step 1: MIDI to WAV using FluidSynth
        fluidsynth_cmd = [
            "fluidsynth",
            "-ni",  # No interactive mode
            "-g", "0.5",  # Gain
            "-T", "wav",  # Output format
            "-F", str(wav_path),  # Output file
            str(soundfont_path),  # Soundfont
            str(midi_path)  # Input MIDI
        ]
        
        logger.debug(f"Running FluidSynth: {' '.join(fluidsynth_cmd)}")
        result = subprocess.run(
            fluidsynth_cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            logger.error(f"FluidSynth failed: {result.stderr}")
            return None
        
        if not wav_path.exists():
            logger.error("FluidSynth did not create WAV file")
            return None
        
        # Step 2: WAV to MP3 using FFmpeg
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", str(wav_path),  # Input WAV
            "-codec:a", "libmp3lame",  # MP3 encoder
            "-b:a", "128k",  # Bitrate
            "-ac", "2",  # Stereo
            "-ar", "44100",  # Sample rate
            "-y",  # Overwrite output
            str(mp3_path)  # Output MP3
        ]
        
        logger.debug(f"Running FFmpeg: {' '.join(ffmpeg_cmd)}")
        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            logger.error(f"FFmpeg failed: {result.stderr}")
            return None
        
        if not mp3_path.exists():
            logger.error("FFmpeg did not create MP3 file")
            return None
        
        # Read MP3 data
        with open(mp3_path, "rb") as f:
            mp3_data = f.read()
        
        logger.info(f"Rendered MIDI to MP3: {len(midi_bytes)} -> {len(mp3_data)} bytes")
        return mp3_data
        
    except subprocess.TimeoutExpired:
        logger.error("MP3 rendering timed out")
        return None
    except Exception as e:
        logger.error(f"MP3 rendering failed: {e}")
        return None
    finally:
        # Cleanup temp directory
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def _find_soundfont() -> Optional[Path]:
    """
    Find available soundfont file.
    
    Returns:
        Path to soundfont file or None if not found
    """
    # Priority order of soundfont locations
    candidates = [
        # Local project soundfont
        Path("GeneralUser.sf2"),
        Path("completed/GeneralUser.sf2"),
        
        # Common system locations
        Path("/usr/share/sounds/sf2/FluidR3_GM.sf2"),
        Path("/usr/share/soundfonts/default.sf2"),
        Path("/usr/share/soundfonts/FluidR3_GM.sf2"),
        Path("/System/Library/Components/CoreAudio.component/Contents/Resources/gs_instruments.dls"),
        
        # macOS
        Path("/usr/local/share/fluidsynth/GeneralUser.sf2"),
        
        # Windows
        Path("C:/soundfonts/GeneralUser.sf2"),
    ]
    
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            logger.debug(f"Found soundfont: {candidate}")
            return candidate
    
    # Try to find any .sf2 file in common directories
    search_dirs = [
        Path("/usr/share/soundfonts"),
        Path("/usr/share/sounds/sf2"),
        Path("/usr/local/share/fluidsynth"),
    ]
    
    for search_dir in search_dirs:
        if search_dir.exists():
            for sf_file in search_dir.glob("*.sf2"):
                logger.debug(f"Found soundfont: {sf_file}")
                return sf_file
    
    logger.warning("No soundfont found")
    return None


def is_rendering_available() -> bool:
    """
    Check if MP3 rendering is available.
    
    Returns:
        True if all dependencies are available
    """
    return RENDER_ENABLED and FLUIDSYNTH_AVAILABLE and FFMPEG_AVAILABLE and (_find_soundfont() is not None)


def get_rendering_status() -> dict:
    """
    Get detailed rendering capability status.
    
    Returns:
        Dictionary with capability details
    """
    return {
        "render_enabled": RENDER_ENABLED,
        "fluidsynth_available": FLUIDSYNTH_AVAILABLE,
        "ffmpeg_available": FFMPEG_AVAILABLE,
        "soundfont_available": _find_soundfont() is not None,
        "fully_available": is_rendering_available()
    }