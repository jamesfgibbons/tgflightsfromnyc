#!/usr/bin/env python3
"""
Rapid iteration workflow for SERP Radio training system.
Implements the "last-mile" checklist for real-world usage.
"""

import json
import subprocess
import sys
import time
from pathlib import Path
import yaml

def check_setup():
    """Check that the system is properly set up."""
    print("🔍 Checking SERP Radio Setup...")
    
    issues = []
    
    # Check required files
    required_files = [
        "2025-08-03T174139Z.midi",
        "motifs_catalog.json", 
        "config/metric_to_label.yaml",
        "labels/2025-08-03T174139Z.labels.csv"
    ]
    
    for file_path in required_files:
        if not Path(file_path).exists():
            issues.append(f"Missing: {file_path}")
    
    # Check for FluidSynth
    try:
        result = subprocess.run(["fluidsynth", "--version"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ FluidSynth available for audio playback")
        else:
            issues.append("FluidSynth not working properly")
    except FileNotFoundError:
        issues.append("FluidSynth not installed (brew install fluidsynth)")
    
    # Check label coverage
    try:
        with open("motifs_catalog.json") as f:
            catalog = json.load(f)
        
        labeled_count = sum(1 for m in catalog.get("motifs", []) 
                           if m.get("label", "UNLABELED") != "UNLABELED")
        total_count = len(catalog.get("motifs", []))
        coverage = (labeled_count / total_count * 100) if total_count > 0 else 0
        
        if coverage < 5:
            issues.append(f"Very low label coverage: {coverage:.1f}% - need more labeled training data")
        elif coverage < 20:
            print(f"⚠️ Low label coverage: {coverage:.1f}% - consider adding more labels")
        else:
            print(f"✅ Label coverage: {coverage:.1f}%")
            
    except Exception as e:
        issues.append(f"Could not check label coverage: {e}")
    
    # Report issues
    if issues:
        print("\n❌ Setup Issues Found:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print("✅ Setup complete - ready for iteration!")
        return True

def show_current_rules():
    """Display current labeling rules."""
    try:
        with open("config/metric_to_label.yaml") as f:
            rules = yaml.safe_load(f)
        
        print("\n📋 Current Labeling Rules:")
        for i, rule in enumerate(rules.get("rules", []), 1):
            conditions = rule.get("when", {})
            label = rule.get("choose_label", "UNKNOWN")
            
            if not conditions:  # Default rule
                print(f"   {i}. DEFAULT → {label}")
            else:
                condition_strs = []
                for metric, threshold in conditions.items():
                    condition_strs.append(f"{metric} {threshold}")
                condition_text = " AND ".join(condition_strs)
                print(f"   {i}. {condition_text} → {label}")
    
    except Exception as e:
        print(f"⚠️ Could not load rules: {e}")

def test_label_decisions():
    """Test label decisions with sample metrics."""
    print("\n🎯 Testing Label Decisions:")
    
    test_scenarios = [
        ("High Performance", {"ctr": 0.8, "position": 0.9, "clicks": 0.7}),
        ("Poor Performance", {"ctr": 0.2, "position": 0.3, "clicks": 0.1}),
        ("High Volatility", {"volatility_index": 0.7}),
        ("Neutral", {"ctr": 0.5, "position": 0.6})
    ]
    
    for name, metrics in test_scenarios:
        # Import here to avoid issues if modules aren't ready
        try:
            from motif_selector import decide_label_from_metrics
            label = decide_label_from_metrics(metrics, "serp")
            print(f"   {name}: {label}")
        except Exception as e:
            print(f"   {name}: ERROR - {e}")

def generate_and_play(iteration: int, custom_metrics: dict = None):
    """Generate MIDI with current rules and play it."""
    output_path = f"/tmp/iteration_{iteration}.mid"
    
    print(f"\n🎵 Generating Iteration {iteration}...")
    
    # Build CLI command
    cmd = [
        sys.executable, "cli.py",
        "--input", "2025-08-03T174139Z.midi",
        "--output", output_path,
        "--source", "demo",
        "--tenant", f"iteration_{iteration}",
        "--demo",
        "--use-training"
    ]
    
    # Run generation
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"✅ Generated: {output_path}")
            
            # Extract label decision from logs
            logs = result.stderr
            if "Label decision:" in logs:
                for line in logs.split('\n'):
                    if "Label decision:" in line:
                        print(f"   🏷️ {line.split('Label decision: ')[1]}")
                        break
            
            # Play the file
            play_midi(output_path)
            return True
            
        else:
            print(f"❌ Generation failed:")
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Generation timed out")
        return False
    except Exception as e:
        print(f"❌ Generation error: {e}")
        return False

def play_midi(midi_path: str):
    """Play MIDI file using system-appropriate method."""
    if not Path(midi_path).exists():
        print(f"❌ File not found: {midi_path}")
        return
    
    # Try FluidSynth first
    soundfont_paths = ["GeneralUser.sf2", "/usr/share/sounds/sf2/GeneralUser.sf2"]
    soundfont = None
    
    for sf_path in soundfont_paths:
        if Path(sf_path).exists():
            soundfont = sf_path
            break
    
    try:
        if soundfont:
            cmd = ["fluidsynth", "-qi", soundfont, midi_path]
        else:
            cmd = ["fluidsynth", "-qi", midi_path]
        
        print(f"🎵 Playing with FluidSynth...")
        subprocess.run(cmd, timeout=10)
        
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # Fall back to system open
        try:
            import platform
            system = platform.system()
            if system == "Darwin":
                subprocess.run(["open", midi_path])
            elif system == "Linux":
                subprocess.run(["xdg-open", midi_path])
            elif system == "Windows":
                import os
                os.startfile(midi_path)
        except Exception as e:
            print(f"⚠️ Could not play audio: {e}")

def interactive_rule_editor():
    """Interactive rule editing workflow."""
    print("\n✏️ Interactive Rule Editor")
    print("=" * 40)
    
    while True:
        print("\nOptions:")
        print("  1. View current rules")
        print("  2. Test label decisions") 
        print("  3. Generate & play with current rules")
        print("  4. Edit rules file (external editor)")
        print("  5. Quick threshold adjustment")
        print("  0. Return to main menu")
        
        choice = input("\nChoice: ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            show_current_rules()
        elif choice == "2":
            test_label_decisions()
        elif choice == "3":
            generate_and_play(int(time.time()) % 1000)
        elif choice == "4":
            print("Opening config/metric_to_label.yaml in system editor...")
            try:
                import platform
                if platform.system() == "Darwin":
                    subprocess.run(["open", "-t", "config/metric_to_label.yaml"])
                else:
                    subprocess.run(["xdg-open", "config/metric_to_label.yaml"])
                
                input("Press ENTER after editing the file...")
                
            except Exception as e:
                print(f"Could not open editor: {e}")
                print("Please edit config/metric_to_label.yaml manually")
        elif choice == "5":
            quick_threshold_adjustment()
        else:
            print("Invalid choice")

def quick_threshold_adjustment():
    """Quick threshold adjustment interface."""
    print("\n🎛️ Quick Threshold Adjustment")
    
    try:
        with open("config/metric_to_label.yaml") as f:
            rules = yaml.safe_load(f)
        
        # Find first rule with thresholds
        for i, rule in enumerate(rules.get("rules", [])):
            conditions = rule.get("when", {})
            if conditions and any(isinstance(v, str) and ">=" in v for v in conditions.values()):
                print(f"\nRule {i+1}: {rule.get('choose_label', 'UNKNOWN')}")
                
                for metric, threshold in conditions.items():
                    if isinstance(threshold, str) and ">=" in threshold:
                        current_val = float(threshold.replace(">=", ""))
                        print(f"  Current {metric}: >= {current_val}")
                        
                        new_val = input(f"  New {metric} threshold (or ENTER to keep): ").strip()
                        if new_val:
                            try:
                                new_threshold = float(new_val)
                                rules["rules"][i]["when"][metric] = f">={new_threshold}"
                                print(f"  Updated {metric}: >= {new_threshold}")
                            except ValueError:
                                print(f"  Invalid value: {new_val}")
                
                # Save changes
                with open("config/metric_to_label.yaml", "w") as f:
                    yaml.dump(rules, f, default_flow_style=False)
                
                print("\n✅ Rules updated!")
                break
        else:
            print("No adjustable thresholds found in rules")
            
    except Exception as e:
        print(f"Error adjusting thresholds: {e}")

def main_menu():
    """Main interactive menu."""
    print("\n🎵 SERP Radio - Rapid Iteration Workflow")
    print("=" * 50)
    
    if not check_setup():
        print("\n❌ Please fix setup issues before continuing")
        return
    
    iteration = 1
    
    while True:
        print(f"\n🚀 Main Menu (Iteration {iteration})")
        print("  1. Generate & Play (quick test)")
        print("  2. Edit Rules (interactive)")
        print("  3. View System Status")
        print("  4. Batch Test Different Metrics")
        print("  5. A/B Compare Two Versions")
        print("  0. Exit")
        
        choice = input("\nChoice: ").strip()
        
        if choice == "0":
            print("👋 Happy sonifying!")
            break
        elif choice == "1":
            if generate_and_play(iteration):
                iteration += 1
        elif choice == "2":
            interactive_rule_editor()
        elif choice == "3":
            check_setup()
            show_current_rules()
            test_label_decisions()
        elif choice == "4":
            batch_test_metrics(iteration)
            iteration += 3
        elif choice == "5":
            ab_compare_workflow(iteration)
            iteration += 2
        else:
            print("Invalid choice")

def batch_test_metrics(start_iteration: int):
    """Test multiple metric scenarios in batch."""
    print("\n🧪 Batch Testing Different Metrics")
    
    scenarios = [
        ("Excellent Performance", {"ctr": 0.9, "position": 0.95, "clicks": 0.85}),
        ("Poor Performance", {"ctr": 0.1, "position": 0.2, "clicks": 0.05}),
        ("High Volatility", {"volatility_index": 0.8, "ctr": 0.5})
    ]
    
    for i, (name, metrics) in enumerate(scenarios):
        print(f"\n🎯 Testing: {name}")
        print(f"   Metrics: {metrics}")
        
        if generate_and_play(start_iteration + i, metrics):
            input("   Press ENTER for next scenario...")

def ab_compare_workflow(iteration: int):
    """A/B compare two rule versions."""
    print("\n⚖️ A/B Comparison Workflow")
    print("1. Current version will be generated first")
    print("2. You can edit rules, then generate version B")
    print("3. Both files will be available for comparison")
    
    # Generate version A
    version_a = f"/tmp/version_a_{iteration}.mid" 
    print(f"\n🅰️ Generating Version A...")
    
    cmd = [sys.executable, "cli.py", "--input", "2025-08-03T174139Z.midi",
           "--output", version_a, "--source", "demo", "--tenant", f"version_a_{iteration}",
           "--demo", "--use-training"]
    
    if subprocess.run(cmd, capture_output=True).returncode == 0:
        print(f"✅ Version A: {version_a}")
        play_midi(version_a)
        
        input("\nNow edit config/metric_to_label.yaml for Version B, then press ENTER...")
        
        # Generate version B
        version_b = f"/tmp/version_b_{iteration}.mid"
        print(f"\n🅱️ Generating Version B...")
        
        cmd[4] = version_b  # Change output path
        cmd[8] = f"version_b_{iteration}"  # Change tenant
        
        if subprocess.run(cmd, capture_output=True).returncode == 0:
            print(f"✅ Version B: {version_b}")
            
            while True:
                choice = input("\nPlay: (A)/(B)/(Q)uit comparison: ").strip().upper()
                if choice == "A":
                    play_midi(version_a)
                elif choice == "B":
                    play_midi(version_b)
                elif choice == "Q":
                    break
    else:
        print("❌ Failed to generate Version A")

if __name__ == "__main__":
    main_menu()