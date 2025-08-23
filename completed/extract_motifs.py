"""
Extract and catalog musical motifs from MIDI files for sonification.
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
import pretty_midi

logger = logging.getLogger(__name__)


def extract_motifs_from_midi(
    midi_path: str,
    bar_length: float = 4.0,
    min_notes: int = 2,
    max_motifs: int = 50
) -> List[Dict[str, Any]]:
    """
    Extract musical motifs from a MIDI file by slicing into bars.
    
    Args:
        midi_path: Path to MIDI file
        bar_length: Length of each bar in beats
        min_notes: Minimum notes required per motif
        max_motifs: Maximum motifs to extract per file
    
    Returns:
        List of motif dictionaries with notes and metadata
    """
    try:
        midi_data = pretty_midi.PrettyMIDI(midi_path)
    except Exception as e:
        logger.error(f"Failed to load MIDI file {midi_path}: {e}")
        return []
    
    if not midi_data.instruments:
        logger.warning(f"No instruments found in {midi_path}")
        return []
    
    motifs = []
    file_name = Path(midi_path).stem
    
    # Calculate bar duration in seconds
    if midi_data.get_tempo_changes()[1]:  # Check if tempo exists
        tempo = midi_data.get_tempo_changes()[1][0]
    else:
        tempo = 120.0  # Default tempo
    
    bar_duration = (bar_length * 60.0) / tempo
    total_duration = midi_data.get_end_time()
    
    # Extract motifs from each instrument
    for instrument_idx, instrument in enumerate(midi_data.instruments):
        if instrument.is_drum:
            continue  # Skip drum tracks for melodic motifs
        
        # Slice into bars
        current_time = 0.0
        bar_idx = 0
        
        while current_time < total_duration and len(motifs) < max_motifs:
            bar_end = current_time + bar_duration
            
            # Get notes in this bar
            bar_notes = [
                note for note in instrument.notes
                if current_time <= note.start < bar_end
            ]
            
            if len(bar_notes) >= min_notes:
                motif = _create_motif_from_notes(
                    bar_notes,
                    file_name,
                    instrument_idx,
                    bar_idx,
                    current_time,
                    bar_duration
                )
                
                if motif:
                    motifs.append(motif)
            
            current_time = bar_end
            bar_idx += 1
    
    # Deduplicate motifs by pitch pattern hash
    unique_motifs = _deduplicate_motifs(motifs)
    
    logger.info(f"Extracted {len(unique_motifs)} unique motifs from {midi_path}")
    return unique_motifs


def _create_motif_from_notes(
    notes: List[pretty_midi.Note],
    file_name: str,
    instrument_idx: int,
    bar_idx: int,
    start_time: float,
    duration: float
) -> Optional[Dict[str, Any]]:
    """Create a motif dictionary from a list of notes."""
    if not notes:
        return None
    
    # Sort notes by start time
    notes = sorted(notes, key=lambda n: n.start)
    
    # Normalize timing relative to bar start
    normalized_notes = []
    for note in notes:
        normalized_notes.append({
            "pitch": note.pitch,
            "velocity": note.velocity,
            "start": note.start - start_time,
            "end": note.end - start_time,
            "duration": note.end - note.start
        })
    
    # Create pitch pattern for hashing
    pitch_pattern = [note["pitch"] for note in normalized_notes]
    pitch_hash = hashlib.md5(str(pitch_pattern).encode()).hexdigest()[:8]
    
    # Calculate motif characteristics
    pitch_range = max(pitch_pattern) - min(pitch_pattern)
    avg_velocity = sum(note["velocity"] for note in normalized_notes) / len(normalized_notes)
    note_density = len(normalized_notes) / duration
    
    motif = {
        "id": f"{file_name}_{instrument_idx}_{bar_idx}_{pitch_hash}",
        "source_file": file_name,
        "instrument_idx": instrument_idx,
        "bar_idx": bar_idx,
        "pitch_hash": pitch_hash,
        "notes": normalized_notes,
        "metadata": {
            "note_count": len(normalized_notes),
            "pitch_range": pitch_range,
            "avg_velocity": int(avg_velocity),
            "note_density": round(note_density, 2),
            "duration": round(duration, 2),
            "lowest_pitch": min(pitch_pattern),
            "highest_pitch": max(pitch_pattern)
        }
    }
    
    return motif


def _deduplicate_motifs(motifs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate motifs based on pitch pattern hash."""
    seen_hashes = set()
    unique_motifs = []
    
    for motif in motifs:
        pitch_hash = motif["pitch_hash"]
        if pitch_hash not in seen_hashes:
            seen_hashes.add(pitch_hash)
            unique_motifs.append(motif)
    
    return unique_motifs


def process_midi_library(
    input_dir: str,
    output_catalog: str = "motifs_catalog.json",
    file_patterns: List[str] = ["*.mid", "*.midi"]
) -> Dict[str, Any]:
    """
    Process a directory of MIDI files to extract motif catalog.
    
    Args:
        input_dir: Directory containing MIDI files
        output_catalog: Output JSON catalog file path
        file_patterns: File patterns to match
    
    Returns:
        Catalog dictionary with motifs and metadata
    """
    input_path = Path(input_dir)
    all_motifs = []
    processed_files = []
    
    # Find all MIDI files
    midi_files = []
    for pattern in file_patterns:
        midi_files.extend(input_path.glob(pattern))
    
    logger.info(f"Found {len(midi_files)} MIDI files to process")
    
    # Process each file
    for midi_file in midi_files:
        try:
            motifs = extract_motifs_from_midi(str(midi_file))
            all_motifs.extend(motifs)
            processed_files.append(str(midi_file.name))
            logger.info(f"Processed {midi_file.name}: {len(motifs)} motifs")
        except Exception as e:
            logger.error(f"Failed to process {midi_file}: {e}")
    
    # Create catalog
    catalog = {
        "version": "1.0",
        "generated_at": str(Path.cwd()),
        "total_motifs": len(all_motifs),
        "processed_files": processed_files,
        "motifs": all_motifs,
        "categories": _categorize_motifs(all_motifs)
    }
    
    # Write catalog to file
    with open(output_catalog, 'w') as f:
        json.dump(catalog, f, indent=2)
    
    logger.info(f"Created motif catalog with {len(all_motifs)} motifs in {output_catalog}")
    return catalog


def _categorize_motifs(motifs: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Categorize motifs by characteristics for easier selection."""
    categories = {
        "low_pitch": [],      # Motifs with low average pitch
        "high_pitch": [],     # Motifs with high average pitch  
        "dense": [],          # High note density
        "sparse": [],         # Low note density
        "wide_range": [],     # Large pitch range
        "narrow_range": [],   # Small pitch range
        "soft": [],           # Low velocity
        "loud": []            # High velocity
    }
    
    for motif in motifs:
        motif_id = motif["id"]
        metadata = motif["metadata"]
        
        # Pitch categories
        avg_pitch = (metadata["lowest_pitch"] + metadata["highest_pitch"]) / 2
        if avg_pitch < 60:  # Below middle C
            categories["low_pitch"].append(motif_id)
        elif avg_pitch > 72:  # Above C5
            categories["high_pitch"].append(motif_id)
        
        # Density categories
        if metadata["note_density"] > 2.0:
            categories["dense"].append(motif_id)
        elif metadata["note_density"] < 0.5:
            categories["sparse"].append(motif_id)
        
        # Range categories
        if metadata["pitch_range"] > 12:  # More than an octave
            categories["wide_range"].append(motif_id)
        elif metadata["pitch_range"] < 5:  # Less than a fourth
            categories["narrow_range"].append(motif_id)
        
        # Velocity categories
        if metadata["avg_velocity"] < 50:
            categories["soft"].append(motif_id)
        elif metadata["avg_velocity"] > 100:
            categories["loud"].append(motif_id)
    
    return categories


def load_motif_catalog(catalog_path: str = "motifs_catalog.json") -> Dict[str, Any]:
    """
    Load motif catalog from JSON file.
    
    Args:
        catalog_path: Path to catalog JSON file
    
    Returns:
        Catalog dictionary
    """
    try:
        with open(catalog_path, 'r') as f:
            catalog = json.load(f)
        logger.info(f"Loaded catalog with {catalog['total_motifs']} motifs")
        return catalog
    except FileNotFoundError:
        logger.error(f"Catalog file not found: {catalog_path}")
        return {"motifs": [], "categories": {}}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in catalog file: {e}")
        return {"motifs": [], "categories": {}}