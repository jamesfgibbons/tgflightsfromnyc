"""
Select appropriate musical motifs based on SERP metrics and controls.
"""

import logging
import random
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from map_to_controls import Controls
from extract_motifs import load_motif_catalog

try:  # Optional FastAI predictor
    from src.training.fastai_runtime import predict_motif_label  # type: ignore
except Exception:  # pragma: no cover - runtime optionality
    predict_motif_label = None  # type: ignore

logger = logging.getLogger(__name__)

# Module-level caches
_CATALOG_CACHE: Optional[Dict[str, Any]] = None
_LABEL_RULES_CACHE: Optional[Dict[str, Any]] = None


def _load_catalog_once(catalog_path: str = "motifs_catalog.json") -> Dict[str, Any]:
    """Load catalog once and cache at module level."""
    global _CATALOG_CACHE
    
    if _CATALOG_CACHE is None:
        _CATALOG_CACHE = load_motif_catalog(catalog_path)
        logger.info(f"Cached motif catalog with {_CATALOG_CACHE.get('total_motifs', 0)} motifs")
    
    return _CATALOG_CACHE


def _load_label_rules_once(rules_path: str = "config/metric_to_label.yaml") -> Dict[str, Any]:
    """Load label rules once and cache at module level."""
    global _LABEL_RULES_CACHE
    
    if _LABEL_RULES_CACHE is None:
        try:
            with open(rules_path, 'r') as f:
                _LABEL_RULES_CACHE = yaml.safe_load(f)
            logger.info(f"Cached label rules from {rules_path}")
        except FileNotFoundError:
            logger.warning(f"Label rules file not found: {rules_path}, using fallback")
            _LABEL_RULES_CACHE = _get_fallback_rules()
        except Exception as e:
            logger.error(f"Error loading label rules: {e}, using fallback")
            _LABEL_RULES_CACHE = _get_fallback_rules()
    
    return _LABEL_RULES_CACHE


def _get_fallback_rules() -> Dict[str, Any]:
    """Get fallback rules when YAML file is unavailable."""
    return {
        "rules": [
            {"when": {"ctr": ">=0.7", "position": ">=0.8"}, "choose_label": "MOMENTUM_POS"},
            {"when": {"ctr": "<0.3", "position": "<0.4"}, "choose_label": "MOMENTUM_NEG"},
            {"when": {}, "choose_label": "NEUTRAL"}
        ],
        "valid_labels": ["MOMENTUM_POS", "MOMENTUM_NEG", "VOLATILE_SPIKE", "NEUTRAL", "UNLABELED"]
    }


def decide_label_from_metrics(
    metrics: Dict[str, float],
    mode: str = "serp",
    rules_path: str = "config/metric_to_label.yaml"
) -> str:
    """
    Decide motif label based on metrics using declarative rules.
    
    Args:
        metrics: Normalized metrics (0-1 range)
        mode: Processing mode ("serp" or "gsc")
        rules_path: Path to YAML rules file
    
    Returns:
        Label string (e.g., "MOMENTUM_POS", "NEUTRAL")
    """
    rules = _load_label_rules_once(rules_path)
    
    # Add mode to metrics for rule evaluation
    extended_metrics = metrics.copy()
    extended_metrics["mode"] = mode
    
    # Evaluate rules in order
    for rule in rules.get("rules", []):
        conditions = rule.get("when", {})
        
        # Check if all conditions are met
        if _evaluate_conditions(extended_metrics, conditions):
            chosen_label = rule.get("choose_label", "NEUTRAL")
            description = rule.get("description", "")
            
            logger.info(f"Label decision: {chosen_label} - {description}")
            return chosen_label
    
    # Fallback if no rules match (shouldn't happen with proper default rule)
    logger.warning("No label rules matched, defaulting to NEUTRAL")
    return "NEUTRAL"


def _evaluate_conditions(metrics: Dict[str, Any], conditions: Dict[str, str]) -> bool:
    """
    Evaluate rule conditions against metrics.
    
    Args:
        metrics: Dictionary of metric values
        conditions: Dictionary of conditions to check
    
    Returns:
        True if all conditions are met
    """
    if not conditions:  # Empty conditions match everything (default rule)
        return True
    
    for metric_name, condition in conditions.items():
        if metric_name not in metrics:
            return False  # Missing metric fails the condition
        
        metric_value = metrics[metric_name]
        
        # Handle string conditions
        if isinstance(condition, str):
            # Parse comparison operators
            if condition.startswith(">="):
                threshold = float(condition[2:])
                if not (metric_value >= threshold):
                    return False
            elif condition.startswith("<="):
                threshold = float(condition[2:])
                if not (metric_value <= threshold):
                    return False
            elif condition.startswith(">"):
                threshold = float(condition[1:])
                if not (metric_value > threshold):
                    return False
            elif condition.startswith("<"):
                threshold = float(condition[1:])
                if not (metric_value < threshold):
                    return False
            elif condition.startswith("==") or condition.startswith("="):
                # Handle string equality (for mode matching)
                expected = condition.replace("==", "").replace("=", "").strip()
                if str(metric_value) != expected:
                    return False
            else:
                # Direct equality
                if str(metric_value) != condition:
                    return False
        else:
            # Direct comparison
            if metric_value != condition:
                return False
    
    return True


def select_motifs_for_controls(
    controls: Controls,
    tenant_id: str,
    num_motifs: int = 4,
    catalog_path: str = "motifs_catalog.json"
) -> List[Dict[str, Any]]:
    """
    Select motifs that complement the given controls.
    
    Args:
        controls: MIDI controls to match motifs against
        tenant_id: Tenant identifier for logging
        num_motifs: Number of motifs to select
        catalog_path: Path to motif catalog
    
    Returns:
        List of selected motif dictionaries
    """
    catalog = _load_catalog_once(catalog_path)
    all_motifs = catalog.get("motifs", [])
    categories = catalog.get("categories", {})
    
    if not all_motifs:
        logger.warning(f"No motifs available for tenant {tenant_id}")
        return _get_fallback_motifs(num_motifs)
    
    # Determine selection strategy based on controls
    strategy = _determine_selection_strategy(controls)
    logger.info(f"Using selection strategy '{strategy}' for tenant {tenant_id}")
    
    # Select motifs based on strategy
    selected_motifs = _select_by_strategy(
        all_motifs, 
        categories, 
        strategy, 
        controls, 
        num_motifs,
        tenant_id
    )
    
    logger.info(f"Selected {len(selected_motifs)} motifs for tenant {tenant_id}: "
               f"{[m['id'] for m in selected_motifs]}")
    
    return selected_motifs


def _determine_selection_strategy(controls: Controls) -> str:
    """Determine motif selection strategy based on controls."""
    # High energy: fast tempo + high velocity
    if controls.bpm > 140 and controls.velocity > 90:
        return "high_energy"
    
    # Ambient: slow tempo + low velocity + high reverb
    elif controls.bpm < 80 and controls.velocity < 50 and controls.reverb_send > 80:
        return "ambient"
    
    # Bright: high filter cutoff + positive transpose
    elif controls.cc74_filter > 90 and controls.transpose > 5:
        return "bright"
    
    # Dark: low filter + negative transpose
    elif controls.cc74_filter < 40 and controls.transpose < -5:
        return "dark"
    
    # Balanced: moderate values across parameters
    else:
        return "balanced"


def _select_by_strategy(
    all_motifs: List[Dict[str, Any]],
    categories: Dict[str, List[str]],
    strategy: str,
    controls: Controls,
    num_motifs: int,
    tenant_id: str
) -> List[Dict[str, Any]]:
    """Select motifs based on the determined strategy."""
    motif_pool = []
    
    if strategy == "high_energy":
        # Prefer dense, loud motifs with wide ranges
        motif_pool = _get_motifs_by_categories(
            all_motifs, categories, 
            ["dense", "loud", "wide_range"]
        )
    
    elif strategy == "ambient":
        # Prefer sparse, soft motifs
        motif_pool = _get_motifs_by_categories(
            all_motifs, categories,
            ["sparse", "soft", "narrow_range"]
        )
    
    elif strategy == "bright":
        # Prefer high-pitch motifs
        motif_pool = _get_motifs_by_categories(
            all_motifs, categories,
            ["high_pitch", "wide_range"]
        )
    
    elif strategy == "dark":
        # Prefer low-pitch motifs
        motif_pool = _get_motifs_by_categories(
            all_motifs, categories,
            ["low_pitch", "narrow_range"]
        )
    
    else:  # balanced
        # Mix from all categories
        motif_pool = all_motifs
    
    # If pool is too small, fall back to all motifs
    if len(motif_pool) < num_motifs:
        logger.warning(f"Motif pool too small ({len(motif_pool)}), using all motifs for tenant {tenant_id}")
        motif_pool = all_motifs
    
    # Deterministic selection based on tenant_id and controls
    selected = _deterministic_selection(motif_pool, num_motifs, tenant_id, controls)
    
    return selected


def _get_motifs_by_categories(
    all_motifs: List[Dict[str, Any]],
    categories: Dict[str, List[str]],
    category_names: List[str]
) -> List[Dict[str, Any]]:
    """Get motifs that match any of the specified categories."""
    motif_ids = set()
    
    for category in category_names:
        if category in categories:
            motif_ids.update(categories[category])
    
    # Return motifs that match the IDs
    return [motif for motif in all_motifs if motif["id"] in motif_ids]


def _deterministic_selection(
    motif_pool: List[Dict[str, Any]],
    num_motifs: int,
    tenant_id: str,
    controls: Controls
) -> List[Dict[str, Any]]:
    """
    Deterministically select motifs based on tenant_id and controls.
    Same inputs will always produce same outputs.
    """
    # Create deterministic seed from tenant_id and controls
    seed_string = f"{tenant_id}_{controls.bpm}_{controls.transpose}_{controls.velocity}"
    seed = hash(seed_string) % (2**32)
    
    # Use seeded random for consistent selection
    rng = random.Random(seed)
    
    # Sort motifs by ID for consistency
    sorted_motifs = sorted(motif_pool, key=lambda m: m["id"])
    
    # Select without replacement
    if len(sorted_motifs) <= num_motifs:
        return sorted_motifs
    
    selected_indices = rng.sample(range(len(sorted_motifs)), num_motifs)
    selected_motifs = [sorted_motifs[i] for i in selected_indices]
    
    return selected_motifs


def _get_fallback_motifs(num_motifs: int) -> List[Dict[str, Any]]:
    """Generate fallback motifs when catalog is empty."""
    fallback_motifs = []
    
    for i in range(num_motifs):
        motif = {
            "id": f"fallback_{i}",
            "source_file": "fallback",
            "instrument_idx": 0,
            "bar_idx": i,
            "pitch_hash": f"fb{i:02d}",
            "notes": [
                {
                    "pitch": 60 + (i * 2),  # C4, D4, E4, F#4
                    "velocity": 64,
                    "start": 0.0,
                    "end": 1.0,
                    "duration": 1.0
                }
            ],
            "metadata": {
                "note_count": 1,
                "pitch_range": 0,
                "avg_velocity": 64,
                "note_density": 1.0,
                "duration": 1.0,
                "lowest_pitch": 60 + (i * 2),
                "highest_pitch": 60 + (i * 2)
            }
        }
        fallback_motifs.append(motif)
    
    logger.warning(f"Generated {num_motifs} fallback motifs")
    return fallback_motifs


def get_motif_by_id(motif_id: str, catalog_path: str = "motifs_catalog.json") -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific motif by ID.
    
    Args:
        motif_id: ID of motif to retrieve
        catalog_path: Path to motif catalog
    
    Returns:
        Motif dictionary or None if not found
    """
    catalog = _load_catalog_once(catalog_path)
    all_motifs = catalog.get("motifs", [])
    
    for motif in all_motifs:
        if motif["id"] == motif_id:
            return motif
    
    logger.warning(f"Motif not found: {motif_id}")
    return None


def filter_motifs_by_criteria(
    tempo_range: Optional[tuple] = None,
    pitch_range: Optional[tuple] = None,
    velocity_range: Optional[tuple] = None,
    min_notes: Optional[int] = None,
    max_notes: Optional[int] = None,
    catalog_path: str = "motifs_catalog.json"
) -> List[Dict[str, Any]]:
    """
    Filter motifs by specific criteria.
    
    Args:
        tempo_range: (min_bpm, max_bpm) tuple
        pitch_range: (lowest_pitch, highest_pitch) tuple  
        velocity_range: (min_velocity, max_velocity) tuple
        min_notes: Minimum number of notes
        max_notes: Maximum number of notes
        catalog_path: Path to motif catalog
    
    Returns:
        List of motifs matching criteria
    """
    catalog = _load_catalog_once(catalog_path)
    all_motifs = catalog.get("motifs", [])
    filtered = []
    
    for motif in all_motifs:
        metadata = motif["metadata"]
        
        # Apply filters
        if pitch_range:
            if not (pitch_range[0] <= metadata["lowest_pitch"] and 
                   metadata["highest_pitch"] <= pitch_range[1]):
                continue
        
        if velocity_range:
            if not (velocity_range[0] <= metadata["avg_velocity"] <= velocity_range[1]):
                continue
        
        if min_notes and metadata["note_count"] < min_notes:
            continue
        
        if max_notes and metadata["note_count"] > max_notes:
            continue
        
        filtered.append(motif)
    
    logger.info(f"Filtered to {len(filtered)} motifs from {len(all_motifs)} total")
    return filtered


def select_motifs_by_label(
    metrics: Dict[str, float],
    mode: str,
    tenant_id: str,
    num_motifs: int = 4,
    catalog_path: str = "motifs_catalog.json",
    rules_path: str = "config/metric_to_label.yaml"
) -> List[Dict[str, Any]]:
    """
    Select motifs based on data-driven label matching.
    
    This is the new training-aware selection method that:
    1. Decides label from metrics using declarative rules
    2. Filters motifs by that label
    3. Falls back to unlabeled motifs if needed
    
    Args:
        metrics: Normalized metrics (0-1 range)
        mode: Processing mode ("serp" or "gsc")
        tenant_id: Tenant identifier for logging
        num_motifs: Number of motifs to select
        catalog_path: Path to motif catalog
        rules_path: Path to label rules YAML
    
    Returns:
        List of selected motif dictionaries
    """
    # Step 1: Decide target label from metrics
    target_label = decide_label_from_metrics(metrics, mode, rules_path)
    
    # Step 2: Load catalog and filter by label
    catalog = _load_catalog_once(catalog_path)
    all_motifs = catalog.get("motifs", [])
    
    if not all_motifs:
        logger.warning(f"No motifs available for tenant {tenant_id}")
        return _get_fallback_motifs(num_motifs)
    
    # Step 3: Filter motifs by target label
    labeled_motifs = [m for m in all_motifs if m.get("label") == target_label]
    
    logger.info(f"Found {len(labeled_motifs)} motifs with label '{target_label}' for tenant {tenant_id}")
    
    # Step 4: If not enough labeled motifs, consult FastAI predictor and/or add unlabeled ones
    if len(labeled_motifs) < num_motifs:
        unlabeled_motifs = [m for m in all_motifs if m.get("label", "UNLABELED") == "UNLABELED"]
        remaining_unlabeled = list(unlabeled_motifs)

        if predict_motif_label:
            predicted_matches: List[Dict[str, Any]] = []
            for motif in unlabeled_motifs:
                try:
                    predicted = predict_motif_label(motif)
                except Exception as exc:  # pragma: no cover - prediction guard
                    logger.debug(f"FastAI predictor failed for motif {motif.get('id')}: {exc}")
                    continue
                if predicted == target_label:
                    predicted_matches.append(motif)

            if predicted_matches:
                logger.info(
                    f"FastAI predictor supplied {len(predicted_matches)} unlabeled motifs for label '{target_label}'"
                )
                labeled_ids = {m["id"] for m in labeled_motifs}
                for motif in predicted_matches:
                    if motif["id"] not in labeled_ids:
                        labeled_motifs.append(motif)
                        labeled_ids.add(motif["id"])
                remaining_unlabeled = [m for m in unlabeled_motifs if m["id"] not in labeled_ids]
            else:
                remaining_unlabeled = unlabeled_motifs

        if len(labeled_motifs) < num_motifs and remaining_unlabeled:
            logger.info(
                f"Adding {len(remaining_unlabeled)} unlabeled motifs to pool after predictor filter"
            )
            labeled_ids = {m["id"] for m in labeled_motifs}
            for motif in remaining_unlabeled:
                if motif["id"] not in labeled_ids:
                    labeled_motifs.append(motif)
                    labeled_ids.add(motif["id"])
    
    # Step 5: If still not enough, fall back to all motifs
    if len(labeled_motifs) < num_motifs:
        logger.warning(f"Not enough labeled motifs, using all {len(all_motifs)} motifs")
        labeled_motifs = all_motifs
    
    # Step 6: Deterministic selection from pool
    # Create a simple seed from tenant_id and target label for label-based selection
    seed_string = f"{tenant_id}_{target_label}_{len(labeled_motifs)}"
    seed = hash(seed_string) % (2**32)
    
    # Use seeded random for consistent selection
    import random
    rng = random.Random(seed)
    
    # Sort motifs by ID for consistency
    sorted_motifs = sorted(labeled_motifs, key=lambda m: m["id"])
    
    # Select without replacement
    if len(sorted_motifs) <= num_motifs:
        selected = sorted_motifs
    else:
        selected_indices = rng.sample(range(len(sorted_motifs)), num_motifs)
        selected = [sorted_motifs[i] for i in selected_indices]
    
    logger.info(f"Selected {len(selected)} motifs for tenant {tenant_id} with label '{target_label}': "
               f"{[m['id'] for m in selected]}")
    
    return selected


def get_training_stats(catalog_path: str = "motifs_catalog.json") -> Dict[str, Any]:
    """
    Get statistics about the training data in the motif catalog.
    
    Args:
        catalog_path: Path to motif catalog
    
    Returns:
        Dictionary with training statistics
    """
    catalog = _load_catalog_once(catalog_path)
    all_motifs = catalog.get("motifs", [])
    
    # Count motifs by label
    label_counts = {}
    total_motifs = len(all_motifs)
    labeled_motifs = 0
    
    for motif in all_motifs:
        label = motif.get("label", "UNLABELED")
        label_counts[label] = label_counts.get(label, 0) + 1
        
        if label != "UNLABELED":
            labeled_motifs += 1
    
    # Calculate percentages
    label_percentages = {
        label: round((count / total_motifs) * 100, 1) 
        for label, count in label_counts.items()
    }
    
    training_ready = labeled_motifs > 0
    coverage = round((labeled_motifs / total_motifs) * 100, 1) if total_motifs > 0 else 0
    
    stats = {
        "total_motifs": total_motifs,
        "labeled_motifs": labeled_motifs,
        "training_ready": training_ready,
        "coverage_percent": coverage,
        "label_distribution": {
            "counts": label_counts,
            "percentages": label_percentages
        },
        "training_metadata": catalog.get("training_metadata", {})
    }
    
    return stats
