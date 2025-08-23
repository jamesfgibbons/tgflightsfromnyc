"""
Classify musical momentum from tokenized motif sections.
"""

import json
import sys
import logging
import statistics
from typing import Dict, List, Any, Tuple
import argparse

logger = logging.getLogger(__name__)


def classify_momentum_from_tokens(token_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify momentum for each tokenized section.
    
    Args:
        token_data: Output from tokenize_motifs.py
    
    Returns:
        Dictionary with momentum classifications
    """
    if token_data.get("error"):
        return token_data  # Pass through errors
    
    tenant_id = token_data["tenant_id"]
    file_id = token_data["file_id"]
    tokens = token_data["tokens"]
    
    if not tokens:
        return {
            "error": True,
            "tenant_id": tenant_id,
            "message": "No tokens to classify"
        }
    
    momentum_results = []
    
    for section in tokens:
        momentum = _classify_section_momentum(section, tenant_id)
        momentum_results.append(momentum)
    
    result = {
        "error": False,
        "tenant_id": tenant_id,
        "file_id": file_id,
        "total_sections": len(tokens),
        "momentum": momentum_results
    }
    
    # Log structured output for each section
    for momentum in momentum_results:
        log_entry = {
            "tenant_id": tenant_id,
            "section_id": momentum["section_id"],
            "label": momentum["label"],
            "score": momentum["score"]
        }
        logger.info(json.dumps(log_entry))
    
    return result


def _classify_section_momentum(section: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
    """
    Classify momentum for a single section.
    
    Momentum score calculation:
    - tempo_norm = clamp((bpm-60)/100, 0, 1)
    - vel_norm = mean_vel/100  
    - pitch_slope_norm = clamp((slope+0.6)/1.2, 0, 1)
    - score = 0.4*tempo_norm + 0.4*vel_norm + 0.2*pitch_slope_norm
    
    Labels:
    - positive: score > 0.65
    - negative: score < 0.35
    - neutral: 0.35 <= score <= 0.65
    """
    section_id = section["section_id"]
    metadata = section["metadata"]
    token_sequence = section["token_sequence"]
    
    # Extract features for momentum classification
    bpm = metadata.get("avg_bpm", 120.0)
    avg_velocity = metadata.get("avg_velocity", 64.0)
    
    # Calculate pitch slope from note events
    pitch_slope = _calculate_pitch_slope(token_sequence)
    
    # Normalize features
    tempo_norm = max(0.0, min(1.0, (bpm - 60.0) / 100.0))
    vel_norm = avg_velocity / 100.0
    pitch_slope_norm = max(0.0, min(1.0, (pitch_slope + 0.6) / 1.2))
    
    # Calculate momentum score
    score = 0.4 * tempo_norm + 0.4 * vel_norm + 0.2 * pitch_slope_norm
    
    # Classify momentum
    if score > 0.65:
        label = "positive"
        explanation = f"High momentum: fast tempo ({bpm:.1f}), loud dynamics ({avg_velocity:.1f}), rising pitch trend"
    elif score < 0.35:
        label = "negative"
        explanation = f"Low momentum: slow tempo ({bpm:.1f}), soft dynamics ({avg_velocity:.1f}), falling pitch trend"
    else:
        label = "neutral"
        explanation = f"Neutral momentum: moderate tempo ({bpm:.1f}), balanced dynamics ({avg_velocity:.1f})"
    
    momentum_result = {
        "section_id": section_id,
        "label": label,
        "score": round(score, 3),
        "explanation": explanation,
        "components": {
            "tempo_norm": round(tempo_norm, 3),
            "velocity_norm": round(vel_norm, 3),
            "pitch_slope_norm": round(pitch_slope_norm, 3),
            "pitch_slope": round(pitch_slope, 3)
        },
        "raw_features": {
            "bpm": bpm,
            "avg_velocity": avg_velocity,
            "note_count": metadata.get("note_count", 0)
        }
    }
    
    return momentum_result


def _calculate_pitch_slope(token_sequence: List[List[Any]]) -> float:
    """
    Calculate pitch slope (trend) from token sequence.
    
    Returns positive value for rising pitch, negative for falling pitch.
    """
    if not token_sequence:
        return 0.0
    
    # Extract NOTE_ON events with timing
    note_events = []
    for token in token_sequence:
        if len(token) >= 4 and token[0] == "NOTE_ON":
            pitch = token[1]
            time = token[3]
            note_events.append((time, pitch))
    
    if len(note_events) < 2:
        return 0.0
    
    # Sort by time
    note_events.sort(key=lambda x: x[0])
    
    # Calculate simple linear regression slope
    times = [event[0] for event in note_events]
    pitches = [event[1] for event in note_events]
    
    if len(set(times)) < 2:  # All notes at same time
        return 0.0
    
    # Simple slope calculation: (y2-y1)/(x2-x1) for first and last points
    time_span = times[-1] - times[0]
    if time_span == 0:
        return 0.0
    
    pitch_change = pitches[-1] - pitches[0]
    slope = pitch_change / time_span
    
    # For more robust calculation, use least squares if enough points
    if len(note_events) >= 5:
        slope = _least_squares_slope(times, pitches)
    
    return slope


def _least_squares_slope(x_values: List[float], y_values: List[float]) -> float:
    """Calculate least squares slope for better trend detection."""
    if len(x_values) != len(y_values) or len(x_values) < 2:
        return 0.0
    
    n = len(x_values)
    x_mean = sum(x_values) / n
    y_mean = sum(y_values) / n
    
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    denominator = sum((x - x_mean) ** 2 for x in x_values)
    
    if denominator == 0:
        return 0.0
    
    return numerator / denominator


def analyze_momentum_distribution(momentum_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze the distribution of momentum classifications.
    
    Args:
        momentum_data: Output from classify_momentum_from_tokens
    
    Returns:
        Analysis summary
    """
    if momentum_data.get("error"):
        return momentum_data
    
    momentum_sections = momentum_data["momentum"]
    
    if not momentum_sections:
        return {
            "error": True,
            "message": "No momentum data to analyze"
        }
    
    # Count labels
    label_counts = {"positive": 0, "negative": 0, "neutral": 0}
    scores = []
    
    for section in momentum_sections:
        label = section["label"]
        score = section["score"]
        
        label_counts[label] += 1
        scores.append(score)
    
    # Calculate statistics
    total_sections = len(momentum_sections)
    analysis = {
        "total_sections": total_sections,
        "label_distribution": {
            label: {
                "count": count,
                "percentage": round((count / total_sections) * 100, 1)
            }
            for label, count in label_counts.items()
        },
        "score_statistics": {
            "mean": round(statistics.mean(scores), 3),
            "median": round(statistics.median(scores), 3),
            "min": round(min(scores), 3),
            "max": round(max(scores), 3),
            "std_dev": round(statistics.stdev(scores) if len(scores) > 1 else 0.0, 3)
        },
        "dominant_momentum": max(label_counts.items(), key=lambda x: x[1])[0],
        "momentum_variance": len(set(label_counts.values())) > 1  # True if mixed momentum
    }
    
    return analysis


def main():
    """CLI entry point for momentum classification."""
    parser = argparse.ArgumentParser(description="Classify momentum from tokenized motifs")
    parser.add_argument("--analyze", action="store_true", help="Include distribution analysis")
    
    args = parser.parse_args()
    
    # Configure logging for structured output
    logging.basicConfig(
        format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
        level=logging.INFO
    )
    
    try:
        # Read token data from stdin
        input_data = sys.stdin.read().strip()
        if not input_data:
            error_output = {
                "error": True,
                "message": "No input data provided on stdin"
            }
            print(json.dumps(error_output), file=sys.stderr)
            sys.exit(1)
        
        token_data = json.loads(input_data)
        
        # Classify momentum
        result = classify_momentum_from_tokens(token_data)
        
        if result.get("error"):
            print(json.dumps(result), file=sys.stderr)
            sys.exit(1)
        
        # Add analysis if requested
        if args.analyze:
            analysis = analyze_momentum_distribution(result)
            result["analysis"] = analysis
        
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
        logger.error(f"Unexpected error in momentum classification: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()