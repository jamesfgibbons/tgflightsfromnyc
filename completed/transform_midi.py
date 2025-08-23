"""
Transform MIDI files by applying sonification controls and motif arrangements.
"""

import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
import pretty_midi
import mido
from map_to_controls import Controls

logger = logging.getLogger(__name__)


def transform_midi_with_controls(
    input_midi_path: str,
    controls: Controls,
    motifs: List[Dict[str, Any]],
    output_midi_path: str,
    tenant_id: str
) -> bool:
    """
    Transform MIDI file by applying controls and arranging motifs.
    
    Args:
        input_midi_path: Path to source MIDI file
        controls: Controls dataclass with transformation parameters
        motifs: List of selected motifs to arrange
        output_midi_path: Path for output MIDI file
        tenant_id: Tenant identifier for logging
    
    Returns:
        True if transformation succeeded, False otherwise
    """
    try:
        # Load input MIDI
        if Path(input_midi_path).exists():
            midi_data = pretty_midi.PrettyMIDI(input_midi_path)
            logger.info(f"Loaded base MIDI file {input_midi_path} for tenant {tenant_id}")
        else:
            # Create empty MIDI if no input file
            midi_data = pretty_midi.PrettyMIDI(initial_tempo=controls.bpm)
            logger.info(f"Created empty MIDI for tenant {tenant_id}")
        
        # Apply tempo transformation
        _apply_tempo_change(midi_data, controls.bpm)
        
        # Apply global transformations to existing instruments
        for instrument in midi_data.instruments:
            if not instrument.is_drum:
                _apply_pitch_transpose(instrument, controls.transpose)
                _apply_velocity_scaling(instrument, controls.velocity)
        
        # Add motif-based instruments
        _add_motif_instruments(midi_data, motifs, controls)
        
        # Add control changes for filter and reverb
        _add_control_changes(midi_data, controls)
        
        # Save transformed MIDI
        midi_data.write(output_midi_path)
        
        # Verify round-trip compatibility with mido
        _verify_midi_compatibility(output_midi_path)
        
        logger.info(f"Successfully transformed MIDI for tenant {tenant_id} -> {output_midi_path}")
        return True
        
    except Exception as e:
        logger.error(f"MIDI transformation failed for tenant {tenant_id}: {e}")
        return False


def _apply_tempo_change(midi_data: pretty_midi.PrettyMIDI, target_bpm: int) -> None:
    """Apply tempo change to MIDI data."""
    # Get current tempo
    tempo_changes = midi_data.get_tempo_changes()
    if len(tempo_changes[1]) > 0:
        current_tempo = tempo_changes[1][0]
    else:
        current_tempo = 120.0
    
    # Calculate tempo ratio
    tempo_ratio = target_bpm / current_tempo
    
    # Apply tempo scaling if significantly different
    if abs(tempo_ratio - 1.0) > 0.05:  # 5% threshold
        # Adjust all timing
        for instrument in midi_data.instruments:
            for note in instrument.notes:
                note.start /= tempo_ratio
                note.end /= tempo_ratio
        
        # Update tempo in MIDI
        midi_data._tick_scales = [tempo_ratio]
        
        logger.debug(f"Applied tempo change: {current_tempo:.1f} -> {target_bpm} BPM")


def _apply_pitch_transpose(instrument: pretty_midi.Instrument, semitones: int) -> None:
    """Apply pitch transposition to instrument."""
    if semitones == 0:
        return
    
    for note in instrument.notes:
        new_pitch = note.pitch + semitones
        # Clamp to MIDI range
        note.pitch = max(0, min(127, new_pitch))
    
    logger.debug(f"Applied transpose: {semitones} semitones to instrument {instrument.program}")


def _apply_velocity_scaling(instrument: pretty_midi.Instrument, target_velocity: int) -> None:
    """Scale velocities towards target while preserving dynamics."""
    if not instrument.notes:
        return
    
    # Calculate current velocity statistics
    velocities = [note.velocity for note in instrument.notes]
    current_avg = sum(velocities) / len(velocities)
    current_range = max(velocities) - min(velocities)
    
    # Scale factor to reach target average
    if current_avg > 0:
        scale_factor = target_velocity / current_avg
    else:
        scale_factor = 1.0
    
    # Apply scaling with range preservation
    for note in instrument.notes:
        scaled_velocity = note.velocity * scale_factor
        # Clamp to MIDI range
        note.velocity = max(1, min(127, int(scaled_velocity)))
    
    logger.debug(f"Applied velocity scaling: factor {scale_factor:.2f} to instrument {instrument.program}")


def _add_motif_instruments(
    midi_data: pretty_midi.PrettyMIDI,
    motifs: List[Dict[str, Any]],
    controls: Controls
) -> None:
    """Add new instruments based on selected motifs."""
    if not motifs:
        return
    
    # Standard arrangement: Bass, Lead, Pad, Arp
    instrument_programs = [33, 81, 89, 1]  # Finger Bass, Lead Square, Pad Warm, Piano
    
    for i, motif in enumerate(motifs[:4]):  # Limit to 4 instruments
        # Create new instrument
        program = instrument_programs[i % len(instrument_programs)]
        instrument = pretty_midi.Instrument(program=program, name=f"Motif_{i}")
        
        # Add motif pattern repeated over time
        _arrange_motif_pattern(instrument, motif, controls, duration=32.0, start_time=0.0)
        
        midi_data.instruments.append(instrument)
        logger.debug(f"Added motif instrument: {motif['id']} as program {program}")


def _arrange_motif_pattern(
    instrument: pretty_midi.Instrument,
    motif: Dict[str, Any],
    controls: Controls,
    duration: float,
    start_time: float = 0.0
) -> None:
    """Arrange a motif pattern over specified duration."""
    motif_notes = motif["notes"]
    motif_duration = motif["metadata"]["duration"]
    
    if motif_duration <= 0:
        motif_duration = 4.0  # Default 4 beats
    
    # Calculate how many repetitions fit in duration
    repetitions = max(1, int(duration / motif_duration))
    
    current_time = start_time
    
    for rep in range(repetitions):
        for note_data in motif_notes:
            # Create note with timing offset
            note = pretty_midi.Note(
                velocity=note_data["velocity"],
                pitch=note_data["pitch"] + controls.transpose,
                start=current_time + note_data["start"],
                end=current_time + note_data["end"]
            )
            
            # Clamp pitch to MIDI range
            note.pitch = max(0, min(127, note.pitch))
            
            # Apply velocity scaling
            scaled_velocity = int(note.velocity * (controls.velocity / 64.0))
            note.velocity = max(1, min(127, scaled_velocity))
            
            instrument.notes.append(note)
        
        current_time += motif_duration


def _add_control_changes(midi_data: pretty_midi.PrettyMIDI, controls: Controls) -> None:
    """Add MIDI control changes for filter and reverb."""
    # Add control changes to first non-drum instrument
    target_instrument = None
    for instrument in midi_data.instruments:
        if not instrument.is_drum:
            target_instrument = instrument
            break
    
    if target_instrument is None:
        # Create a control instrument if none exists
        target_instrument = pretty_midi.Instrument(program=0, name="Control")
        midi_data.instruments.append(target_instrument)
    
    # Add filter cutoff (CC74)
    filter_cc = pretty_midi.ControlChange(
        number=74,  # Filter cutoff
        value=controls.cc74_filter,
        time=0.0
    )
    target_instrument.control_changes.append(filter_cc)
    
    # Add reverb send (CC91)
    reverb_cc = pretty_midi.ControlChange(
        number=91,  # Reverb send
        value=controls.reverb_send,
        time=0.0
    )
    target_instrument.control_changes.append(reverb_cc)
    
    logger.debug(f"Added control changes: Filter={controls.cc74_filter}, Reverb={controls.reverb_send}")


def _verify_midi_compatibility(midi_path: str) -> None:
    """Verify MIDI file can be loaded and saved with mido."""
    try:
        # Test mido round-trip
        midi_file = mido.MidiFile(midi_path)
        
        # Create temporary file for test save
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=True) as temp_file:
            midi_file.save(temp_file.name)
        
        logger.debug(f"MIDI compatibility verified for {midi_path}")
        
    except Exception as e:
        logger.warning(f"MIDI compatibility issue in {midi_path}: {e}")
        raise


def create_sonified_midi(
    controls: Controls,
    motifs: List[Dict[str, Any]],
    output_path: str,
    tenant_id: str,
    base_template: Optional[str] = None
) -> bool:
    """
    Create a new sonified MIDI file from controls and motifs.
    
    Args:
        controls: Controls dataclass with parameters
        motifs: List of motifs to arrange
        output_path: Output MIDI file path
        tenant_id: Tenant identifier for logging
        base_template: Optional base MIDI template to start from
    
    Returns:
        True if creation succeeded, False otherwise
    """
    try:
        # Create new MIDI with tempo from controls
        midi_data = pretty_midi.PrettyMIDI(initial_tempo=controls.bpm)
        
        # Load base template if provided
        if base_template and Path(base_template).exists():
            template_midi = pretty_midi.PrettyMIDI(base_template)
            # Copy template instruments as base layer
            for instrument in template_midi.instruments:
                midi_data.instruments.append(instrument)
            logger.info(f"Loaded base template {base_template} for tenant {tenant_id}")
        
        # Add motif-based arrangement
        _add_motif_instruments(midi_data, motifs, controls)
        
        # Add control changes
        _add_control_changes(midi_data, controls)
        
        # Apply global transformations
        for instrument in midi_data.instruments:
            if not instrument.is_drum:
                _apply_pitch_transpose(instrument, controls.transpose)
                _apply_velocity_scaling(instrument, controls.velocity)
        
        # Save result
        midi_data.write(output_path)
        _verify_midi_compatibility(output_path)
        
        logger.info(f"Created sonified MIDI for tenant {tenant_id}: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create sonified MIDI for tenant {tenant_id}: {e}")
        return False


def batch_transform_midis(
    input_dir: str,
    output_dir: str,
    controls: Controls,
    motifs: List[Dict[str, Any]],
    tenant_id: str
) -> Dict[str, bool]:
    """
    Batch transform multiple MIDI files with same controls.
    
    Args:
        input_dir: Directory containing input MIDI files
        output_dir: Directory for output files
        controls: Controls to apply to all files
        motifs: Motifs to add to all files
        tenant_id: Tenant identifier
    
    Returns:
        Dictionary mapping filename to success status
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    results = {}
    
    # Find all MIDI files
    midi_files = list(input_path.glob("*.mid")) + list(input_path.glob("*.midi"))
    
    for midi_file in midi_files:
        output_file = output_path / f"transformed_{midi_file.name}"
        
        success = transform_midi_with_controls(
            str(midi_file),
            controls,
            motifs,
            str(output_file),
            tenant_id
        )
        
        results[midi_file.name] = success
    
    logger.info(f"Batch transformation complete for tenant {tenant_id}: "
               f"{sum(results.values())}/{len(results)} succeeded")
    
    return results