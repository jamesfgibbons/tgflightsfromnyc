"""
Label bars in MIDI files for training data-driven motif selection.
Supports both CSV label files and MIDI marker events.
"""

import json
import csv
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import pretty_midi
from extract_motifs import load_motif_catalog

logger = logging.getLogger(__name__)


def extract_midi_markers(midi_path: str) -> Dict[int, str]:
    """
    Extract marker/text events from MIDI file and map to bar indices.
    
    Args:
        midi_path: Path to MIDI file
    
    Returns:
        Dictionary mapping bar_index to label
    """
    try:
        midi_data = pretty_midi.PrettyMIDI(midi_path)
    except Exception as e:
        logger.error(f"Failed to load MIDI file {midi_path}: {e}")
        return {}
    
    markers = {}
    
    # Extract text/marker events
    for instrument in midi_data.instruments:
        # Check for text events (lyrics, markers)
        if hasattr(instrument, 'lyrics') and instrument.lyrics:
            for lyric in instrument.lyrics:
                # Convert time to approximate bar index (assuming 4/4, 120 BPM)
                bar_index = int(lyric.time // 2.0)  # Rough bar calculation
                if lyric.text.upper().startswith(('MOMENTUM_', 'VOLATILE_', 'NEUTRAL')):
                    markers[bar_index] = lyric.text.upper()
                    logger.info(f"Found marker at bar {bar_index}: {lyric.text}")
    
    # Also check MIDI file level markers
    if hasattr(midi_data, 'markers'):
        for marker in midi_data.markers:
            bar_index = int(marker.time // 2.0)
            if marker.text.upper().startswith(('MOMENTUM_', 'VOLATILE_', 'NEUTRAL')):
                markers[bar_index] = marker.text.upper()
                logger.info(f"Found file marker at bar {bar_index}: {marker.text}")
    
    return markers


def load_csv_labels(csv_path: str) -> Dict[int, Tuple[str, str]]:
    """
    Load labels from CSV file.
    
    Args:
        csv_path: Path to CSV file with columns: bar_index, label, description
    
    Returns:
        Dictionary mapping bar_index to (label, description)
    """
    labels = {}
    
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['bar_index'].startswith('#'):  # Skip comments
                    continue
                
                bar_index = int(row['bar_index'])
                label = row['label'].strip().upper()
                description = row.get('description', '').strip()
                
                labels[bar_index] = (label, description)
                logger.info(f"Loaded label: bar {bar_index} -> {label}")
    
    except FileNotFoundError:
        logger.error(f"Label file not found: {csv_path}")
    except Exception as e:
        logger.error(f"Error reading label file {csv_path}: {e}")
    
    return labels


def apply_labels_to_bars(
    bars_data: Dict[str, Any],
    labels: Dict[int, Tuple[str, str]]
) -> Dict[str, Any]:
    """
    Apply labels to bars data structure.
    
    Args:
        bars_data: Output from extract_bars.py
        labels: Dictionary mapping bar_index to (label, description)
    
    Returns:
        Updated bars data with labels attached
    """
    if bars_data.get("error"):
        return bars_data
    
    labeled_bars = []
    label_stats = {"labeled": 0, "total": len(bars_data["bars"])}
    
    for bar in bars_data["bars"]:
        bar_index = bar["bar_index"]
        
        # Add label if we have one for this bar
        if bar_index in labels:
            label, description = labels[bar_index]
            bar["label"] = label
            bar["label_description"] = description
            bar["is_labeled"] = True
            label_stats["labeled"] += 1
            logger.info(f"Applied label to bar {bar_index}: {label}")
        else:
            bar["label"] = "UNLABELED"
            bar["label_description"] = ""
            bar["is_labeled"] = False
        
        labeled_bars.append(bar)
    
    # Update the data structure
    bars_data["bars"] = labeled_bars
    bars_data["label_stats"] = label_stats
    bars_data["training_ready"] = label_stats["labeled"] > 0
    
    logger.info(f"Labeled {label_stats['labeled']} of {label_stats['total']} bars")
    return bars_data


def propagate_labels_to_motifs(
    labeled_bars: Dict[str, Any],
    catalog_path: str = "motifs_catalog.json"
) -> Dict[str, Any]:
    """
    Propagate bar labels to motif catalog.
    
    Args:
        labeled_bars: Labeled bars data
        catalog_path: Path to motifs catalog
    
    Returns:
        Updated motif catalog with labels
    """
    # Load existing catalog
    catalog = load_motif_catalog(catalog_path)
    
    if not catalog.get("motifs"):
        logger.warning("No motifs found in catalog")
        return catalog
    
    # Create mapping from bar_index to label
    bar_labels = {}
    for bar in labeled_bars["bars"]:
        bar_labels[bar["bar_index"]] = {
            "label": bar["label"],
            "description": bar["label_description"],
            "is_labeled": bar["is_labeled"]
        }
    
    # Update motifs with labels
    labeled_motifs = []
    for motif in catalog["motifs"]:
        # Extract bar index from motif metadata
        bar_idx = motif.get("bar_idx", -1)
        
        if bar_idx in bar_labels:
            motif["label"] = bar_labels[bar_idx]["label"]
            motif["label_description"] = bar_labels[bar_idx]["description"]
            motif["is_labeled"] = bar_labels[bar_idx]["is_labeled"]
        else:
            motif["label"] = "UNLABELED"
            motif["label_description"] = ""
            motif["is_labeled"] = False
        
        labeled_motifs.append(motif)
    
    # Update catalog
    catalog["motifs"] = labeled_motifs
    catalog["training_metadata"] = {
        "labeled_bars": labeled_bars["label_stats"]["labeled"],
        "total_bars": labeled_bars["label_stats"]["total"],
        "training_ready": labeled_bars["training_ready"],
        "last_labeled": str(Path().cwd())
    }
    
    # Count labeled motifs by category
    label_counts = {}
    for motif in labeled_motifs:
        label = motif["label"]
        label_counts[label] = label_counts.get(label, 0) + 1
    
    catalog["training_metadata"]["label_distribution"] = label_counts
    
    logger.info(f"Updated catalog with label distribution: {label_counts}")
    return catalog


def main():
    """CLI entry point for bar labeling."""
    parser = argparse.ArgumentParser(description="Label bars for training motif selection")
    parser.add_argument("midi_file", help="Path to MIDI file")
    parser.add_argument("--labels", help="Path to CSV labels file")
    parser.add_argument("--use-markers", action="store_true", 
                       help="Extract labels from MIDI marker events")
    parser.add_argument("--output", default="labeled_bars.json", 
                       help="Output path for labeled bars JSON")
    parser.add_argument("--update-catalog", action="store_true",
                       help="Update motifs catalog with labels")
    parser.add_argument("--tenant", default="training",
                       help="Tenant ID for bar extraction")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
        level=logging.INFO
    )
    
    if not Path(args.midi_file).exists():
        logger.error(f"MIDI file not found: {args.midi_file}")
        return 1
    
    try:
        # Step 1: Extract bars from MIDI
        logger.info(f"Extracting bars from {args.midi_file}")
        
        from extract_bars import extract_bars_from_midi
        bars_data = extract_bars_from_midi(args.midi_file, args.tenant)
        
        if bars_data.get("error"):
            logger.error(f"Bar extraction failed: {bars_data['message']}")
            return 1
        
        logger.info(f"Extracted {bars_data['total_bars']} bars")
        
        # Step 2: Collect labels from various sources
        all_labels = {}
        
        # From CSV file
        if args.labels and Path(args.labels).exists():
            csv_labels = load_csv_labels(args.labels)
            all_labels.update({k: v for k, v in csv_labels.items()})
            logger.info(f"Loaded {len(csv_labels)} labels from CSV")
        
        # From MIDI markers
        if args.use_markers:
            midi_labels = extract_midi_markers(args.midi_file)
            # Convert to tuple format for consistency
            midi_label_tuples = {k: (v, f"From MIDI marker") for k, v in midi_labels.items()}
            all_labels.update(midi_label_tuples)
            logger.info(f"Loaded {len(midi_labels)} labels from MIDI markers")
        
        if not all_labels:
            logger.warning("No labels found! Use --labels or --use-markers")
            # Continue anyway, creating unlabeled structure
        
        # Step 3: Apply labels to bars
        labeled_bars = apply_labels_to_bars(bars_data, all_labels)
        
        # Step 4: Save labeled bars
        with open(args.output, 'w') as f:
            json.dump(labeled_bars, f, indent=2)
        
        logger.info(f"Saved labeled bars to {args.output}")
        
        # Step 5: Update motifs catalog if requested
        if args.update_catalog:
            logger.info("Updating motifs catalog with labels...")
            catalog = propagate_labels_to_motifs(labeled_bars)
            
            with open("motifs_catalog.json", 'w') as f:
                json.dump(catalog, f, indent=2)
            
            logger.info("Updated motifs_catalog.json with training labels")
        
        # Print summary
        stats = labeled_bars["label_stats"]
        print(f"\n✅ Labeling Summary:")
        print(f"   📊 Total bars: {stats['total']}")
        print(f"   🏷️  Labeled bars: {stats['labeled']}")
        print(f"   📈 Training ready: {labeled_bars['training_ready']}")
        print(f"   💾 Output: {args.output}")
        
        if args.update_catalog:
            training_meta = catalog.get("training_metadata", {})
            dist = training_meta.get("label_distribution", {})
            print(f"   🎯 Label distribution: {dist}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Labeling failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())