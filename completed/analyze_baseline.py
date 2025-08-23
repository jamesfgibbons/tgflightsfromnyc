#!/usr/bin/env python3
"""
Analyze and process the baseline MIDI file for SERP Radio.
"""

import logging
from pathlib import Path
from extract_motifs import extract_motifs_from_midi, process_midi_library
from transform_midi import transform_midi_with_controls, create_sonified_midi
from map_to_controls import Controls, map_metrics_to_controls
from motif_selector import select_motifs_for_controls

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_baseline_midi():
    """Analyze the baseline MIDI file and extract motifs."""
    baseline_path = "2025-08-03T174139Z.midi"
    
    if not Path(baseline_path).exists():
        logger.error(f"Baseline MIDI file not found: {baseline_path}")
        return
    
    logger.info(f"Analyzing baseline MIDI: {baseline_path}")
    
    # Extract motifs from baseline
    motifs = extract_motifs_from_midi(
        baseline_path,
        bar_length=4.0,
        min_notes=1,  # Allow single notes as motifs
        max_motifs=100  # Extract more motifs from baseline
    )
    
    logger.info(f"Extracted {len(motifs)} motifs from baseline")
    
    # Create catalog with just the baseline
    catalog = {
        "version": "1.0",
        "generated_at": str(Path.cwd()),
        "total_motifs": len(motifs),
        "processed_files": [baseline_path],
        "motifs": motifs,
        "categories": _categorize_motifs(motifs)
    }
    
    # Save catalog
    import json
    with open("motifs_catalog.json", 'w') as f:
        json.dump(catalog, f, indent=2)
    
    logger.info("Created motifs_catalog.json from baseline")
    
    # Print motif summary
    print_motif_summary(motifs)
    
    return motifs

def _categorize_motifs(motifs):
    """Categorize motifs by characteristics."""
    categories = {
        "low_pitch": [],
        "high_pitch": [],
        "dense": [],
        "sparse": [],
        "wide_range": [],
        "narrow_range": [],
        "soft": [],
        "loud": []
    }
    
    for motif in motifs:
        motif_id = motif["id"]
        metadata = motif["metadata"]
        
        avg_pitch = (metadata["lowest_pitch"] + metadata["highest_pitch"]) / 2
        if avg_pitch < 60:
            categories["low_pitch"].append(motif_id)
        elif avg_pitch > 72:
            categories["high_pitch"].append(motif_id)
        
        if metadata["note_density"] > 2.0:
            categories["dense"].append(motif_id)
        elif metadata["note_density"] < 0.5:
            categories["sparse"].append(motif_id)
        
        if metadata["pitch_range"] > 12:
            categories["wide_range"].append(motif_id)
        elif metadata["pitch_range"] < 5:
            categories["narrow_range"].append(motif_id)
        
        if metadata["avg_velocity"] < 50:
            categories["soft"].append(motif_id)
        elif metadata["avg_velocity"] > 100:
            categories["loud"].append(motif_id)
    
    return categories

def print_motif_summary(motifs):
    """Print summary of extracted motifs."""
    if not motifs:
        print("No motifs extracted!")
        return
    
    print(f"\n=== MOTIF SUMMARY ({len(motifs)} total) ===")
    
    # Group by instrument
    by_instrument = {}
    for motif in motifs:
        inst_idx = motif["instrument_idx"]
        if inst_idx not in by_instrument:
            by_instrument[inst_idx] = []
        by_instrument[inst_idx].append(motif)
    
    for inst_idx, inst_motifs in by_instrument.items():
        print(f"\nInstrument {inst_idx}: {len(inst_motifs)} motifs")
        
        # Show first few motifs as examples
        for i, motif in enumerate(inst_motifs[:3]):
            meta = motif["metadata"]
            print(f"  {motif['id']}: {meta['note_count']} notes, "
                  f"pitch {meta['lowest_pitch']}-{meta['highest_pitch']}, "
                  f"vel {meta['avg_velocity']}, density {meta['note_density']:.1f}")
        
        if len(inst_motifs) > 3:
            print(f"  ... and {len(inst_motifs) - 3} more")

def test_sonification():
    """Test the complete sonification pipeline with sample metrics."""
    logger.info("Testing sonification pipeline...")
    
    # Sample SERP metrics (normalized 0-1)
    test_metrics = {
        "ctr": 0.75,        # High CTR
        "impressions": 0.6,  # Medium impressions
        "position": 0.2,     # Good position (lower is better, so 0.2 = position ~8)
        "clicks": 0.8        # High clicks
    }
    
    # Map to controls
    controls = map_metrics_to_controls(test_metrics, "test_tenant", "serp")
    logger.info(f"Generated controls: BPM={controls.bpm}, transpose={controls.transpose}")
    
    # Select motifs
    motifs = select_motifs_for_controls(controls, "test_tenant", num_motifs=4)
    logger.info(f"Selected {len(motifs)} motifs")
    
    # Create sonified output
    success = create_sonified_midi(
        controls=controls,
        motifs=motifs,
        output_path="test_sonified_output.midi",
        tenant_id="test_tenant",
        base_template="2025-08-03T174139Z.midi"
    )
    
    if success:
        logger.info("✅ Sonification test successful! Created test_sonified_output.midi")
    else:
        logger.error("❌ Sonification test failed")
    
    return success

if __name__ == "__main__":
    print("🎵 SERP Radio - Baseline MIDI Analysis")
    
    # Step 1: Analyze baseline and extract motifs
    motifs = analyze_baseline_midi()
    
    if motifs:
        print(f"\n✅ Successfully processed baseline MIDI")
        print(f"📁 Created motifs_catalog.json with {len(motifs)} motifs")
        
        # Step 2: Test the sonification pipeline
        print(f"\n🧪 Testing sonification pipeline...")
        test_sonification()
        
        print(f"\n🎉 Setup complete! Your MIDI samples are ready for sonification.")
        print(f"📖 Use the other modules to convert SERP metrics to music.")
    else:
        print(f"\n❌ Failed to process baseline MIDI")