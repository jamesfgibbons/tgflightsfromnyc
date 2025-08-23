"""
Extract bars from MIDI files with time signature tracking and fingerprinting.
"""

import json
import sys
import hashlib
import logging
from typing import Dict, List, Any, Tuple, Optional
import pretty_midi
import argparse

logger = logging.getLogger(__name__)


def extract_bars_from_midi(
    midi_path: str,
    tenant_id: str,
    bars_per_section: int = 4
) -> Dict[str, Any]:
    """
    Extract bars from MIDI file with time signature tracking.
    
    Args:
        midi_path: Path to MIDI file
        tenant_id: Tenant identifier
        bars_per_section: Number of bars per section (default 4)
    
    Returns:
        Dictionary with bar extraction results
    """
    try:
        midi_data = pretty_midi.PrettyMIDI(midi_path)
    except Exception as e:
        error_msg = f"Failed to load MIDI file {midi_path}: {e}"
        logger.error(error_msg)
        return {
            "error": True,
            "tenant_id": tenant_id,
            "message": error_msg
        }
    
    if not midi_data.instruments:
        error_msg = f"No instruments found in {midi_path}"
        logger.error(error_msg)
        return {
            "error": True,
            "tenant_id": tenant_id,
            "message": error_msg
        }
    
    # Get time signature changes
    time_signatures = midi_data.time_signature_changes
    if not time_signatures:
        # Default to 4/4 if no time signature specified
        time_signatures = [pretty_midi.TimeSignature(4, 4, 0.0)]
    
    # Get tempo changes
    tempo_times, tempos = midi_data.get_tempo_changes()
    if len(tempos) == 0:
        tempos = [120.0]  # Default tempo
        tempo_times = [0.0]
    
    # Extract bars
    bars = []
    file_id = midi_path.split('/')[-1].replace('.midi', '').replace('.mid', '')
    
    # Calculate bars based on time signatures
    current_time = 0.0
    bar_index = 0
    total_duration = midi_data.get_end_time()
    
    for ts_idx, time_sig in enumerate(time_signatures):
        # Calculate when this time signature ends
        if ts_idx + 1 < len(time_signatures):
            ts_end_time = time_signatures[ts_idx + 1].time
        else:
            ts_end_time = total_duration
        
        # Calculate bar duration for this time signature
        current_tempo = _get_tempo_at_time(tempo_times, tempos, time_sig.time)
        quarter_note_duration = 60.0 / current_tempo
        bar_duration = quarter_note_duration * time_sig.numerator
        
        # Extract bars within this time signature
        ts_start_time = max(current_time, time_sig.time)
        bar_start_time = ts_start_time
        
        while bar_start_time < ts_end_time:
            bar_end_time = min(bar_start_time + bar_duration, ts_end_time)
            
            # Extract notes in this bar from all instruments
            bar_notes = []
            for instrument in midi_data.instruments:
                if instrument.is_drum:
                    continue  # Skip drum tracks for now
                
                for note in instrument.notes:
                    if bar_start_time <= note.start < bar_end_time:
                        bar_notes.append({
                            "pitch": note.pitch,
                            "velocity": note.velocity,
                            "start": note.start - bar_start_time,  # Relative to bar start
                            "duration": note.end - note.start
                        })
            
            # Create bar fingerprint
            bar_hash = _create_bar_fingerprint(bar_notes)
            
            # Get tempo for this bar
            bar_tempo = _get_tempo_at_time(tempo_times, tempos, bar_start_time)
            
            bar_data = {
                "bar_index": bar_index,
                "time_signature": f"{time_sig.numerator}/{time_sig.denominator}",
                "start_sec": round(bar_start_time, 3),
                "end_sec": round(bar_end_time, 3),
                "bpm": round(bar_tempo, 1),
                "notes": bar_notes,
                "hash": bar_hash
            }
            
            bars.append(bar_data)
            bar_index += 1
            bar_start_time = bar_end_time
            
            if bar_start_time >= bar_end_time:
                break
        
        current_time = ts_end_time
    
    result = {
        "error": False,
        "tenant_id": tenant_id,
        "file_id": file_id,
        "total_bars": len(bars),
        "bars": bars
    }
    
    logger.info(f"Extracted {len(bars)} bars from {midi_path} for tenant {tenant_id}")
    return result


def _get_tempo_at_time(tempo_times: List[float], tempos: List[float], time: float) -> float:
    """Get tempo at specific time, carrying forward last known tempo."""
    if not tempos:
        return 120.0
    
    # Find the tempo change that applies at this time
    current_tempo = tempos[0]
    for i, tempo_time in enumerate(tempo_times):
        if tempo_time <= time:
            current_tempo = tempos[i]
        else:
            break
    
    return current_tempo


def _create_bar_fingerprint(notes: List[Dict[str, Any]]) -> str:
    """Create SHA-256 fingerprint of bar based on pitch, velocity, duration."""
    if not notes:
        return hashlib.sha256(b"empty").hexdigest()[:16]
    
    # Sort notes by start time for consistent ordering
    sorted_notes = sorted(notes, key=lambda n: n["start"])
    
    # Create fingerprint data
    fingerprint_data = []
    for note in sorted_notes:
        fingerprint_data.extend([
            note["pitch"],
            note["velocity"],
            round(note["duration"], 3)  # Round to avoid floating point precision issues
        ])
    
    # Create hash
    fingerprint_str = str(fingerprint_data)
    return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]


def main():
    """CLI entry point for bar extraction."""
    parser = argparse.ArgumentParser(description="Extract bars from MIDI file")
    parser.add_argument("midi_file", help="Path to MIDI file")
    parser.add_argument("--tenant", required=True, help="Tenant ID")
    parser.add_argument("--bars", type=int, default=4, help="Bars per section (default: 4)")
    
    args = parser.parse_args()
    
    # Configure logging to output structured JSON
    logging.basicConfig(
        format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
        level=logging.INFO
    )
    
    try:
        result = extract_bars_from_midi(args.midi_file, args.tenant, args.bars)
        
        if result.get("error"):
            # Output error JSON and exit with code 1
            error_output = {
                "tenant_id": args.tenant,
                "error": True,
                "message": result["message"]
            }
            print(json.dumps(error_output), file=sys.stderr)
            sys.exit(1)
        else:
            # Output success JSON to stdout
            print(json.dumps(result, indent=2))
            sys.exit(0)
    
    except Exception as e:
        error_output = {
            "tenant_id": args.tenant,
            "error": True,
            "message": f"Unexpected error: {str(e)}"
        }
        print(json.dumps(error_output), file=sys.stderr)
        logger.error(f"Unexpected error processing {args.midi_file}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()