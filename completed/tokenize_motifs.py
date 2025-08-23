"""
Tokenize musical motifs by grouping bars into sections and deduplicating.
"""

import json
import sys
import hashlib
import logging
from typing import Dict, List, Any, Tuple
import argparse

logger = logging.getLogger(__name__)


def tokenize_motifs_from_bars(
    bars_data: Dict[str, Any],
    section_size: int = 4
) -> Dict[str, Any]:
    """
    Group bars into sections and create deduplicated tokens.
    
    Args:
        bars_data: Output from extract_bars.py
        section_size: Number of bars per section
    
    Returns:
        Dictionary with tokenized sections
    """
    if bars_data.get("error"):
        return bars_data  # Pass through errors
    
    tenant_id = bars_data["tenant_id"]
    file_id = bars_data["file_id"]
    bars = bars_data["bars"]
    
    if not bars:
        return {
            "error": True,
            "tenant_id": tenant_id,
            "message": "No bars to tokenize"
        }
    
    # Group bars into sections
    sections = []
    section_id = 0
    
    for i in range(0, len(bars), section_size):
        section_bars = bars[i:i + section_size]
        
        if len(section_bars) < section_size:
            # Handle incomplete sections at the end
            if len(section_bars) >= 1:  # Process any section with at least 1 bar
                # Pad with empty bars to reach section_size
                while len(section_bars) < section_size:
                    empty_bar = {
                        "bar_index": section_bars[-1]["bar_index"] + 1,
                        "time_signature": section_bars[-1]["time_signature"],
                        "start_sec": section_bars[-1]["end_sec"],
                        "end_sec": section_bars[-1]["end_sec"] + 2.0,  # Assume 2-second bars
                        "bpm": section_bars[-1]["bpm"],
                        "notes": [],
                        "hash": "empty"
                    }
                    section_bars.append(empty_bar)
            else:
                break  # Skip empty sections
        
        # Create token sequence for this section
        token_sequence = _create_token_sequence(section_bars)
        
        # Create section hash for deduplication
        section_hash = _create_section_hash(token_sequence)
        
        section_data = {
            "section_id": f"{file_id}_section_{section_id}",
            "hash": section_hash,
            "bars_covered": len([b for b in section_bars if b["notes"]]),  # Count non-empty bars
            "start_bar": section_bars[0]["bar_index"],
            "end_bar": section_bars[-1]["bar_index"],
            "token_sequence": token_sequence,
            "metadata": _extract_section_metadata(section_bars)
        }
        
        sections.append(section_data)
        section_id += 1
    
    # Deduplicate sections by hash
    unique_sections = _deduplicate_sections(sections)
    
    result = {
        "error": False,
        "tenant_id": tenant_id,
        "file_id": file_id,
        "total_sections": len(sections),
        "unique_sections": len(unique_sections),
        "tokens": unique_sections
    }
    
    logger.info(f"Tokenized {len(sections)} sections, {len(unique_sections)} unique for {file_id}")
    return result


def _create_token_sequence(bars: List[Dict[str, Any]]) -> List[List[Any]]:
    """
    Create a token sequence from bars.
    
    Format: [["NOTE_ON", pitch, velocity, start_time], ["NOTE_OFF", pitch, 0, end_time], ...]
    """
    token_sequence = []
    
    for bar_idx, bar in enumerate(bars):
        bar_start_offset = bar_idx * 4.0  # Assume 4-beat bars for token timing
        
        # Collect all note events
        events = []
        
        for note in bar["notes"]:
            # Note on event
            events.append({
                "time": bar_start_offset + note["start"],
                "type": "NOTE_ON",
                "pitch": note["pitch"],
                "velocity": note["velocity"]
            })
            
            # Note off event
            events.append({
                "time": bar_start_offset + note["start"] + note["duration"],
                "type": "NOTE_OFF",
                "pitch": note["pitch"],
                "velocity": 0
            })
        
        # Sort events by time
        events.sort(key=lambda e: (e["time"], e["type"] == "NOTE_OFF"))  # NOTE_ON before NOTE_OFF at same time
        
        # Convert to token format
        for event in events:
            token = [
                event["type"],
                event["pitch"],
                event["velocity"],
                round(event["time"], 3)
            ]
            token_sequence.append(token)
    
    return token_sequence


def _create_section_hash(token_sequence: List[List[Any]]) -> str:
    """Create hash for section deduplication."""
    if not token_sequence:
        return hashlib.sha256(b"empty_section").hexdigest()[:16]
    
    # Create normalized representation for hashing
    # Remove timing information to focus on pitch/rhythm patterns
    normalized_tokens = []
    
    for token in token_sequence:
        if len(token) >= 3:
            # Include type, pitch, velocity but normalize timing
            normalized_token = [token[0], token[1], token[2]]
            normalized_tokens.append(normalized_token)
    
    # Create hash from normalized tokens
    token_str = str(normalized_tokens)
    return hashlib.sha256(token_str.encode()).hexdigest()[:16]


def _extract_section_metadata(bars: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract metadata from section bars."""
    all_notes = []
    total_duration = 0.0
    bpm_sum = 0.0
    
    for bar in bars:
        all_notes.extend(bar["notes"])
        total_duration += bar["end_sec"] - bar["start_sec"]
        bpm_sum += bar["bpm"]
    
    if not all_notes:
        return {
            "note_count": 0,
            "avg_pitch": 0.0,
            "avg_velocity": 0.0,
            "avg_bpm": bpm_sum / len(bars) if bars else 120.0,
            "pitch_range": 0,
            "duration": total_duration
        }
    
    pitches = [note["pitch"] for note in all_notes]
    velocities = [note["velocity"] for note in all_notes]
    
    metadata = {
        "note_count": len(all_notes),
        "avg_pitch": sum(pitches) / len(pitches),
        "avg_velocity": sum(velocities) / len(velocities),
        "avg_bpm": bpm_sum / len(bars),
        "pitch_range": max(pitches) - min(pitches),
        "duration": total_duration,
        "lowest_pitch": min(pitches),
        "highest_pitch": max(pitches)
    }
    
    return metadata


def _deduplicate_sections(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate sections based on hash."""
    seen_hashes = set()
    unique_sections = []
    
    for section in sections:
        section_hash = section["hash"]
        if section_hash not in seen_hashes:
            seen_hashes.add(section_hash)
            unique_sections.append(section)
        else:
            # Log duplicate for debugging
            logger.debug(f"Duplicate section found: {section['section_id']} (hash: {section_hash})")
    
    return unique_sections


def main():
    """CLI entry point for motif tokenization."""
    parser = argparse.ArgumentParser(description="Tokenize motifs from bar data")
    parser.add_argument("--sections", type=int, default=4, help="Bars per section (default: 4)")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
        level=logging.INFO
    )
    
    try:
        # Read bars data from stdin
        input_data = sys.stdin.read().strip()
        if not input_data:
            error_output = {
                "error": True,
                "message": "No input data provided on stdin"
            }
            print(json.dumps(error_output), file=sys.stderr)
            sys.exit(1)
        
        bars_data = json.loads(input_data)
        
        # Tokenize motifs
        result = tokenize_motifs_from_bars(bars_data, args.sections)
        
        if result.get("error"):
            print(json.dumps(result), file=sys.stderr)
            sys.exit(1)
        else:
            print(json.dumps(result, indent=2))
            sys.exit(0)
    
    except json.JSONDecodeError as e:
        error_output = {
            "error": True,
            "message": f"Invalid JSON input: {str(e)}"
        }
        print(json.dumps(error_output), file=sys.stderr)
        sys.exit(1)
    
    except Exception as e:
        error_output = {
            "error": True,
            "message": f"Unexpected error: {str(e)}"
        }
        print(json.dumps(error_output), file=sys.stderr)
        logger.error(f"Unexpected error in tokenization: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()