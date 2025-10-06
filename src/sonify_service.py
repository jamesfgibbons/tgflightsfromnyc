"""
Sonification orchestration service for SERP Radio production backend.
Integrates existing domain modules without reimplementing logic.
"""

import json
import logging
import os
import tempfile
from pathlib import Path
import uuid
from typing import Dict, Any, Optional, List

# Import existing domain modules
import sys
sys.path.append(str(Path(__file__).parent.parent / "completed"))

from completed.fetch_metrics import collect_metrics
from completed.map_to_controls import map_metrics_to_controls, get_fallback_controls
from completed.extract_bars import extract_bars_from_midi
from completed.tokenize_motifs import tokenize_motifs_from_bars
from completed.classify_momentum import classify_momentum_from_tokens
from completed.motif_selector import select_motifs_by_label, select_motifs_for_controls
from completed.transform_midi import create_sonified_midi

from .models import SonifyRequest
from .storage import (
    put_bytes,
    write_json,
    read_text_s3,
    ensure_tenant_prefix,
    get_storage_backend,
    get_supabase_client,
    get_s3_client,
)
from .renderer import render_midi_to_mp3
from .scene_planner import build_scene_schedule

logger = logging.getLogger(__name__)


class SonificationService:
    """Orchestrates complete sonification pipeline."""
    
    def __init__(self, s3_bucket: str):
        self.s3_bucket = s3_bucket
        self.rules_s3 = os.getenv("RULES_S3")
        self.motif_catalog_s3 = os.getenv("MOTIF_CATALOG_S3")
        self.token_bar_window = int(os.getenv("TOKEN_BAR_WINDOW", "4"))
        self.render_mp3 = os.getenv("RENDER_MP3", "0") == "1"
        self.earcons_enabled = os.getenv("EARCONS_ENABLED", "0") == "1"
    
    def run_sonification(
        self,
        request: SonifyRequest,
        input_midi_key: Optional[str],
        output_base_key: Optional[str]
    ) -> Dict[str, Any]:
        """
        Execute complete sonification pipeline.
        
        Args:
            request: Sonification request parameters
            input_midi_key: S3 key for input MIDI file
            output_base_key: Base S3 key for outputs (without extension)
        
        Returns:
            Dictionary with artifact keys and metadata
        """
        tenant = request.tenant
        logger.info(f"Starting sonification for tenant {tenant}, job_id derived from output_base_key")
        
        try:
            # Establish safe output base if not provided
            if not output_base_key:
                safe_id = str(uuid.uuid4())
                output_base_key = ensure_tenant_prefix(tenant, "midi_output", safe_id)

            # Step 1: Resolve metrics
            metrics = self._resolve_metrics(request)
            logger.info(f"Resolved metrics for {tenant}: {list(metrics.keys())}")
            
            # Step 2: Optional momentum analysis
            # Prefer explicitly provided momentum segments from override_metrics if present
            momentum_data: Optional[Dict[str, Any]] = None
            if isinstance(request.override_metrics, dict) and request.override_metrics.get("momentum_data"):
                momentum_data = {"momentum": request.override_metrics.get("momentum_data")}
                logger.info("Using provided momentum bands from override_metrics")
            elif request.momentum:
                try:
                    # Only attempt analysis if we have an input key
                    if input_midi_key:
                        momentum_data = self._run_momentum_analysis(input_midi_key, tenant)
                        logger.info(
                            f"Momentum analysis complete: {momentum_data.get('total_sections', 0)} sections"
                        )
                    else:
                        logger.info("No input MIDI key provided; skipping momentum analysis")
                except Exception as me:
                    # Never fail the whole job on momentum issues
                    logger.warning(f"Skipping momentum due to error: {me}")
                    momentum_data = None
            
            # Step 3: Map metrics to controls or use trained selection
            if request.use_training:
                # Use label-based trained selection
                selected_motifs = self._select_motifs_by_training(
                    metrics, request.source, tenant, request.seed
                )
                # Still need controls for MIDI transformation
                controls = map_metrics_to_controls(metrics, tenant, request.source)
            else:
                # Traditional controls-based selection
                controls = map_metrics_to_controls(metrics, tenant, request.source)
                selected_motifs = self._select_motifs_for_controls(
                    controls, tenant, request.seed
                )
            
            logger.info(f"Selected {len(selected_motifs)} motifs for {tenant}")
            
            # Step 4: Generate MIDI with controls and motifs
            midi_key = f"{output_base_key}.mid"
            
            # Detect earcon triggers from momentum data
            earcons_to_layer = []
            if self.earcons_enabled and momentum_data:
                earcons_to_layer = self._detect_earcon_triggers(momentum_data)
            
            success = self._create_midi(
                controls, selected_motifs, input_midi_key, midi_key, tenant, earcons_to_layer
            )
            
            if not success:
                raise RuntimeError("MIDI generation failed")
            
            # Step 5: Optional MP3 rendering
            mp3_key = None
            if self.render_mp3:
                mp3_key = self._render_to_mp3(midi_key, f"{output_base_key}.mp3")
            
            # Step 6: Save momentum analysis to S3 
            momentum_key = None
            if momentum_data:
                momentum_key = ensure_tenant_prefix(tenant, "logs", f"{Path(output_base_key).name}_momentum.json")
                write_json(self.s3_bucket, momentum_key, momentum_data)
            
            # Step 7: Generate label summary
            label_summary = self._generate_label_summary(selected_motifs)
            
            # Return artifact keys
            result = {
                "midi_key": midi_key,
                "mp3_key": mp3_key,
                "momentum_key": momentum_key,
                "label_summary": label_summary,
                # convenience echo-through for callers that want inline momentum
                "momentum_data": momentum_data.get("momentum") if isinstance(momentum_data, dict) else None
            }
            
            logger.info(f"Sonification complete for {tenant}: {list(result.keys())}")
            return result
            
        except Exception as e:
            logger.error(f"Sonification failed for {tenant}: {e}")
            raise
    
    def _resolve_metrics(self, request: SonifyRequest) -> Dict[str, float]:
        """Resolve metrics from request parameters."""
        if request.source == "demo":
            if request.override_metrics:
                logger.info(f"Using override metrics for {request.tenant}")
                numeric = {
                    k: float(v)
                    for k, v in request.override_metrics.items()
                    if isinstance(v, (int, float))
                }
                if numeric:
                    return numeric
            # Demo mode fallback
            return {"ctr": 0.5, "impressions": 0.5, "position": 0.5, "clicks": 0.5}

        # Use existing fetch_metrics module
        metrics_result = collect_metrics(
            tenant_id=request.tenant,
            mode=request.source,
            lookback=request.lookback
        )
        
        if not metrics_result.get("success"):
            logger.warning(f"Failed to collect metrics for {request.tenant}, using fallback")
            # Fallback metrics
            return {"ctr": 0.5, "impressions": 0.5, "position": 0.5, "clicks": 0.5}

        return metrics_result["normalized_metrics"]
    
    def _run_momentum_analysis(self, input_midi_key: str, tenant: str) -> Dict[str, Any]:
        """Run the momentum analysis pipeline."""
        # If the provided key is a local file path, use it directly
        if input_midi_key and Path(input_midi_key).exists():
            temp_midi_path = input_midi_key
        else:
            # Download input MIDI to temp file for processing (TODO: implement remote fetch)
            with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as temp_file:
                # Note: In production, implement S3/Supabase download here
                temp_midi_path = temp_file.name
        
        try:
            # Step 1: Extract bars
            bars_data = extract_bars_from_midi(
                temp_midi_path, tenant, bars_per_section=self.token_bar_window
            )
            
            if bars_data.get("error"):
                raise RuntimeError(f"Bar extraction failed: {bars_data['message']}")
            
            # Step 2: Tokenize motifs
            token_data = tokenize_motifs_from_bars(bars_data, section_size=self.token_bar_window)
            
            if token_data.get("error"):
                raise RuntimeError(f"Tokenization failed: {token_data['message']}")
            
            # Step 3: Classify momentum
            momentum_data = classify_momentum_from_tokens(token_data)
            
            if momentum_data.get("error"):
                raise RuntimeError(f"Momentum classification failed: {momentum_data['message']}")
            
            return momentum_data
            
        finally:
            # Cleanup temp file if it was a temporary download
            if temp_midi_path and Path(temp_midi_path).exists() and Path(temp_midi_path) != Path(input_midi_key):
                Path(temp_midi_path).unlink(missing_ok=True)
    
    def _select_motifs_by_training(
        self, metrics: Dict[str, float], source: str, tenant: str, seed: Optional[int] = None
    ) -> list:
        """Select motifs using trained rules or model with optional seed."""
        try:
            # Set deterministic seed if provided
            if seed is not None:
                import random
                random.seed(seed)
            
            # Use existing motif_selector with training
            motifs = select_motifs_by_label(
                metrics=metrics,
                mode=source,
                tenant_id=tenant,
                num_motifs=4
            )
            return motifs
        except Exception as e:
            logger.warning(f"Trained selection failed for {tenant}: {e}, using fallback")
            # Fallback to controls-based selection
            controls = get_fallback_controls(tenant)
            return self._select_motifs_for_controls(controls, tenant, seed)
    
    def _select_motifs_for_controls(
        self, controls, tenant: str, seed: Optional[int] = None
    ) -> list:
        """Select motifs using controls-based selection with optional seed."""
        if seed is not None:
            import random
            random.seed(seed)
        
        return select_motifs_for_controls(controls, tenant, num_motifs=4)
    
    def _detect_earcon_triggers(self, momentum_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect momentum transitions that should trigger earcons."""
        earcons = []
        
        momentum_sections = momentum_data.get("momentum", [])
        if not momentum_sections:
            return earcons
        
        prev_label = None
        for i, section in enumerate(momentum_sections):
            current_label = section.get("label")
            section_id = section.get("section_id")
            
            # First section - check if positive
            if i == 0 and current_label == "MOMENTUM_POS":
                earcons.append({
                    "type": "positive",
                    "section_id": section_id,
                    "file": "soundpacks/fanfare_pos.mid",
                    "timing": "start"
                })
                logger.info(f"Earcon trigger: positive fanfare at section {section_id} (first section)")
            
            # Transition detection
            elif prev_label and prev_label != current_label:
                if current_label == "MOMENTUM_POS":
                    earcons.append({
                        "type": "positive",
                        "section_id": section_id,
                        "file": "soundpacks/fanfare_pos.mid",
                        "timing": "transition"
                    })
                    logger.info(f"Earcon trigger: positive fanfare at section {section_id} (transition from {prev_label})")
                
                elif current_label == "MOMENTUM_NEG":
                    earcons.append({
                        "type": "negative", 
                        "section_id": section_id,
                        "file": "soundpacks/hit_neg.mid",
                        "timing": "transition"
                    })
                    logger.info(f"Earcon trigger: negative hit at section {section_id} (transition from {prev_label})")
            
            prev_label = current_label
        
        return earcons
    
    def _create_midi(
        self, controls, motifs: list, input_key: str, output_key: str, tenant: str, 
        earcons: List[Dict[str, Any]] = None
    ) -> bool:
        """Create sonified MIDI and upload to S3."""
        try:
            # Use temporary local file for MIDI creation
            with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as temp_output:
                temp_output_path = temp_output.name
            
            # Use existing transform_midi module
            # If a local base template is provided, use it
            base_template = input_key if input_key and Path(input_key).exists() else None

            # Build a simple scene schedule from momentum (chorus lift on positive)
            scene_schedule = None
            try:
                if momentum_data:
                    bars = int(getattr(request, 'total_bars', 16) or 16)
                    scene_schedule = build_scene_schedule(momentum_data, total_bars=bars)
            except Exception:
                scene_schedule = None

            success = create_sonified_midi(
                controls=controls,
                motifs=motifs,
                output_path=temp_output_path,
                tenant_id=tenant,
                base_template=base_template,
                scene_schedule=scene_schedule,
            )
            
            if success and earcons:
                # Layer earcons onto the generated MIDI
                success = self._layer_earcons(temp_output_path, earcons)
            
            if success:
                # Apply headroom for earcons if enabled
                if earcons and self.render_mp3:
                    self._apply_earcon_headroom(temp_output_path)
                
                # Upload MIDI to S3
                with open(temp_output_path, "rb") as f:
                    midi_data = f.read()
                put_bytes(self.s3_bucket, output_key, midi_data, "audio/midi")
                logger.info(f"MIDI uploaded to s3://{self.s3_bucket}/{output_key}")
            
            return success
            
        except Exception as e:
            logger.error(f"MIDI creation failed for {tenant}: {e}")
            return False
        finally:
            # Cleanup temp file
            Path(temp_output_path).unlink(missing_ok=True)
    
    def _layer_earcons(self, midi_file_path: str, earcons: List[Dict[str, Any]]) -> bool:
        """Layer earcon MIDI files onto main MIDI."""
        try:
            import mido
            
            # Load main MIDI file
            main_midi = mido.MidiFile(midi_file_path)
            
            for earcon in earcons:
                earcon_file = earcon["file"]
                if not Path(earcon_file).exists():
                    logger.warning(f"Earcon file not found: {earcon_file}")
                    continue
                
                # Load earcon MIDI
                earcon_midi = mido.MidiFile(earcon_file)
                
                # Create new track for earcon
                earcon_track = mido.MidiTrack()
                
                # Calculate timing offset (simplified - at start of section)
                section_offset = 0  # TODO: Calculate actual section timing
                
                # Copy earcon messages with timing offset
                for msg in earcon_midi.tracks[0]:
                    if msg.type in ['note_on', 'note_off', 'program_change', 'control_change']:
                        new_msg = msg.copy()
                        if hasattr(new_msg, 'time') and new_msg.time == 0:
                            new_msg.time = section_offset
                        earcon_track.append(new_msg)
                
                # Add earcon track to main MIDI
                main_midi.tracks.append(earcon_track)
                logger.info(f"Layered earcon: {earcon['type']} at section {earcon['section_id']}")
            
            # Save modified MIDI
            main_midi.save(midi_file_path)
            return True
            
        except Exception as e:
            logger.error(f"Failed to layer earcons: {e}")
            return False
    
    def _apply_earcon_headroom(self, midi_file_path: str) -> None:
        """Apply -2dB headroom by reducing velocities."""
        try:
            import mido
            
            midi_file = mido.MidiFile(midi_file_path)
            headroom_factor = 0.79  # Approximately -2dB
            
            for track in midi_file.tracks:
                for msg in track:
                    if msg.type == 'note_on' and hasattr(msg, 'velocity'):
                        msg.velocity = int(msg.velocity * headroom_factor)
            
            midi_file.save(midi_file_path)
            logger.info("Applied -2dB headroom for earcon compatibility")
            
        except Exception as e:
            logger.error(f"Failed to apply headroom: {e}")
    
    def _render_to_mp3(self, midi_key: str, mp3_key: str) -> Optional[str]:
        """Render MIDI to MP3 if enabled."""
        if not self.render_mp3:
            return None
        
        try:
            midi_data = self._load_midi_bytes(midi_key)
            if not midi_data:
                raise RuntimeError("No MIDI data available for rendering")

            # Use renderer module
            mp3_data = render_midi_to_mp3(midi_data)
            
            if mp3_data:
                put_bytes(self.s3_bucket, mp3_key, mp3_data, "audio/mpeg")
                logger.info(f"MP3 uploaded to s3://{self.s3_bucket}/{mp3_key}")
                return mp3_key
            
        except Exception as e:
            logger.error(f"MP3 rendering failed: {e}")
        
        return None

    def _load_midi_bytes(self, midi_key: str) -> Optional[bytes]:
        """Load MIDI bytes from configured storage backend."""
        backend = get_storage_backend()
        try:
            if backend == "supabase":
                client = get_supabase_client()
                result = client.storage.from_(self.s3_bucket).download(midi_key)
                if hasattr(result, "read"):
                    return result.read()
                return bytes(result)
            else:
                s3_client = get_s3_client()
                obj = s3_client.get_object(Bucket=self.s3_bucket, Key=midi_key)
                return obj["Body"].read()
        except Exception as e:
            logger.error(f"Failed to load MIDI bytes for {midi_key}: {e}")
            return None
    
    def _generate_label_summary(self, motifs: list) -> Dict[str, int]:
        """Generate summary of labels used in motif selection."""
        label_counts = {}
        
        for motif in motifs:
            label = motif.get("label", "UNLABELED")
            label_counts[label] = label_counts.get(label, 0) + 1
        
        return label_counts


# Factory function for dependency injection
def create_sonification_service(s3_bucket: str) -> SonificationService:
    """Create sonification service instance."""
    return SonificationService(s3_bucket)
