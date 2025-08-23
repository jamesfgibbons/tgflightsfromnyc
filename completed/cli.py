"""
Command-line interface for SERP Radio with momentum analysis.
Integrates existing sonification with new momentum classification pipeline.
"""

import os
import sys
import json
import tempfile
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import logging
import argparse

# Import new momentum modules
from fetch_metrics import collect_metrics
from map_to_controls import map_metrics_to_controls, get_fallback_controls
from motif_selector import select_motifs_for_controls, select_motifs_by_label
from transform_midi import create_sonified_midi, transform_midi_with_controls

logger = logging.getLogger(__name__)


def setup_logging():
    """Configure logging for structured output."""
    logging.basicConfig(
        format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
        level=logging.INFO
    )


def run_momentum_pipeline(
    input_midi: str,
    tenant_id: str,
    output_path: str
) -> Dict[str, Any]:
    """
    Run the momentum analysis pipeline on MIDI input.
    
    Args:
        input_midi: Path to input MIDI file
        tenant_id: Tenant identifier
        output_path: Path for momentum JSON output
    
    Returns:
        Dictionary with pipeline results
    """
    logger.info(f"Running momentum pipeline for tenant {tenant_id}")
    
    try:
        # Step 1: Extract bars
        bars_result = subprocess.run([
            sys.executable, "extract_bars.py", 
            input_midi, "--tenant", tenant_id
        ], capture_output=True, text=True, check=True)
        
        bars_data = json.loads(bars_result.stdout)
        
        # Step 2: Tokenize motifs
        tokenize_result = subprocess.run([
            sys.executable, "tokenize_motifs.py"
        ], input=bars_result.stdout, capture_output=True, text=True, check=True)
        
        token_data = json.loads(tokenize_result.stdout)
        
        # Step 3: Classify momentum
        momentum_result = subprocess.run([
            sys.executable, "classify_momentum.py", "--analyze"
        ], input=tokenize_result.stdout, capture_output=True, text=True, check=True)
        
        momentum_data = json.loads(momentum_result.stdout)
        
        # Save momentum results
        with open(output_path, 'w') as f:
            json.dump(momentum_data, f, indent=2)
        
        logger.info(f"Momentum pipeline complete. Results saved to {output_path}")
        
        return {
            "success": True,
            "bars_extracted": bars_data.get("total_bars", 0),
            "sections_analyzed": momentum_data.get("total_sections", 0),
            "dominant_momentum": momentum_data.get("analysis", {}).get("dominant_momentum", "unknown"),
            "output_file": output_path
        }
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Pipeline failed: {e.stderr}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
    
    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in pipeline: {e}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="SERP Radio CLI with momentum analysis")
    parser.add_argument("--input", required=True, help="Input MIDI file")
    parser.add_argument("--output", help="Output MIDI file (default: auto-generated)")
    parser.add_argument("--tenant", help="Tenant ID (required for --momentum or real data)")
    parser.add_argument("--source", choices=["demo", "gsc", "serp"], default="demo", 
                       help="Data source mode")
    parser.add_argument("--lookback", default="7d", help="Lookback period for metrics")
    parser.add_argument("--momentum", action="store_true", 
                       help="Run momentum analysis pipeline")
    parser.add_argument("--demo", action="store_true", 
                       help="Use demo mode with sample metrics")
    parser.add_argument("--use-training", action="store_true",
                       help="Use trained label-based motif selection")
    
    args = parser.parse_args()
    
    setup_logging()
    
    # Validate arguments
    if (args.momentum or args.source != "demo") and not args.tenant:
        print("Error: --tenant is required when using --momentum or real data sources", file=sys.stderr)
        sys.exit(1)
    
    if not Path(args.input).exists():
        print(f"Error: Input MIDI file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    # Set default tenant for demo mode
    tenant_id = args.tenant or "demo_tenant"
    
    try:
        print(f"🎵 SERP Radio - Processing {args.input}")
        print(f"📊 Mode: {args.source}, Tenant: {tenant_id}")
        
        # Step 1: Run momentum analysis if requested
        momentum_results = None
        if args.momentum:
            print("🔄 Running momentum analysis...")
            
            momentum_output = f"/tmp/momentum_{tenant_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            momentum_results = run_momentum_pipeline(args.input, tenant_id, momentum_output)
            
            if momentum_results["success"]:
                print(f"✅ Momentum analysis complete:")
                print(f"   📊 Bars extracted: {momentum_results['bars_extracted']}")
                print(f"   🎭 Sections analyzed: {momentum_results['sections_analyzed']}")
                print(f"   📈 Dominant momentum: {momentum_results['dominant_momentum']}")
                print(f"   💾 Results: {momentum_results['output_file']}")
            else:
                print(f"❌ Momentum analysis failed: {momentum_results['error']}")
                if not args.demo:  # Continue with demo mode even if momentum fails
                    sys.exit(1)
        
        # Step 2: Collect metrics
        print(f"📈 Collecting {args.source} metrics...")
        
        if args.demo or args.source == "demo":
            # Use sample metrics for demo
            metrics_result = {
                "success": True,
                "normalized_metrics": {
                    "ctr": 0.65,
                    "impressions": 0.75,
                    "position": 0.3,  # Good position
                    "clicks": 0.8
                }
            }
            print("✅ Using demo metrics")
        else:
            metrics_result = collect_metrics(tenant_id, args.source, args.lookback)
            
            if not metrics_result["success"]:
                print(f"❌ Failed to collect metrics: {metrics_result.get('error', 'Unknown error')}")
                print("🔄 Falling back to demo metrics...")
                metrics_result = {
                    "success": True,
                    "normalized_metrics": {"ctr": 0.5, "impressions": 0.5, "position": 0.5, "clicks": 0.5}
                }
        
        # Step 3: Map metrics to controls
        print("🎛️ Mapping metrics to MIDI controls...")
        
        try:
            controls = map_metrics_to_controls(
                metrics_result["normalized_metrics"], 
                tenant_id, 
                args.source
            )
        except Exception as e:
            print(f"⚠️ Control mapping failed, using fallback: {e}")
            controls = get_fallback_controls(tenant_id)
        
        print(f"✅ Generated controls: BPM={controls.bpm}, transpose={controls.transpose}")
        
        # Step 4: Select motifs
        print("🎼 Selecting musical motifs...")
        
        try:
            if args.use_training:
                # Use new label-based selection
                motifs = select_motifs_by_label(
                    metrics_result["normalized_metrics"],
                    args.source, 
                    tenant_id, 
                    num_motifs=4
                )
                print(f"✅ Selected {len(motifs)} motifs using trained label selection")
            else:
                # Use original controls-based selection
                motifs = select_motifs_for_controls(controls, tenant_id, num_motifs=4)
                print(f"✅ Selected {len(motifs)} motifs using controls-based selection")
        except Exception as e:
            print(f"⚠️ Motif selection failed: {e}")
            motifs = []
        
        # Step 5: Generate output MIDI
        output_path = args.output or f"/tmp/serp_output_{tenant_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mid"
        
        print("🎵 Creating sonified MIDI...")
        
        if motifs:
            # Create new sonified MIDI with motifs
            success = create_sonified_midi(
                controls=controls,
                motifs=motifs,
                output_path=output_path,
                tenant_id=tenant_id,
                base_template=args.input
            )
        else:
            # Transform existing MIDI with controls only
            success = transform_midi_with_controls(
                input_midi_path=args.input,
                controls=controls,
                motifs=[],
                output_midi_path=output_path,
                tenant_id=tenant_id
            )
        
        if success:
            print(f"✅ SERP Radio output created: {output_path}")
            
            # Print summary
            print(f"\n📋 Session Summary:")
            print(f"   🎼 Input: {args.input}")
            print(f"   🎵 Output: {output_path}")
            print(f"   👤 Tenant: {tenant_id}")
            print(f"   📊 Mode: {args.source}")
            print(f"   🎛️ BPM: {controls.bpm}, Transpose: {controls.transpose}")
            if momentum_results and momentum_results["success"]:
                print(f"   📈 Momentum: {momentum_results['dominant_momentum']}")
            
            # Save session metadata
            session_data = {
                "timestamp": datetime.now().isoformat(),
                "input_file": args.input,
                "output_file": output_path,
                "tenant_id": tenant_id,
                "source_mode": args.source,
                "controls": {
                    "bpm": controls.bpm,
                    "transpose": controls.transpose,
                    "velocity": controls.velocity,
                    "filter": controls.cc74_filter,
                    "reverb": controls.reverb_send
                },
                "metrics": metrics_result.get("normalized_metrics", {}),
                "motifs_used": len(motifs),
                "momentum_analysis": momentum_results
            }
            
            session_file = f"/tmp/session_{tenant_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            print(f"   💾 Session data: {session_file}")
            print(f"\n🎉 SERP Radio processing complete!")
            
        else:
            print("❌ Failed to create output MIDI")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


def demo_mode():
    """Run a quick demo with built-in sample."""
    print("🎵 SERP Radio Demo Mode")
    
    # Check if baseline MIDI exists
    baseline_midi = "2025-08-03T174139Z.midi"
    if not Path(baseline_midi).exists():
        print(f"❌ Baseline MIDI not found: {baseline_midi}")
        print("   Please ensure your baseline MIDI file is in the current directory")
        return
    
    # Run with demo settings
    demo_args = [
        "--input", baseline_midi,
        "--source", "demo",
        "--tenant", "demo_tenant", 
        "--demo",
        "--momentum"
    ]
    
    # Temporarily modify sys.argv for argument parsing
    original_argv = sys.argv[:]
    sys.argv = ["cli.py"] + demo_args
    
    try:
        main()
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # No arguments provided, run demo
        demo_mode()
    else:
        main()