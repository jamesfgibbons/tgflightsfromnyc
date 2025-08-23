#!/usr/bin/env python3
"""
Audio playback utility for SERP Radio MIDI files.
Handles cross-platform playback and rapid iteration workflow.
"""

import os
import sys
import platform
import subprocess
import argparse
from pathlib import Path

def find_soundfont():
    """Find available SoundFont files."""
    possible_paths = [
        "GeneralUser.sf2",
        "/usr/share/sounds/sf2/GeneralUser.sf2",
        "/usr/local/share/sounds/sf2/GeneralUser.sf2",
        "/System/Library/Components/CoreAudio.component/Contents/Resources/gs_instruments.dls"
    ]
    
    for path in possible_paths:
        if Path(path).exists():
            return path
    
    return None

def play_midi_mac(midi_path: str, soundfont: str = None):
    """Play MIDI on macOS using FluidSynth."""
    try:
        if soundfont and Path(soundfont).exists():
            cmd = ["fluidsynth", "-qi", soundfont, midi_path]
        else:
            # Try without soundfont - FluidSynth might have defaults
            cmd = ["fluidsynth", "-qi", midi_path]
        
        print(f"🎵 Playing {midi_path} with FluidSynth...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"⚠️ FluidSynth error: {result.stderr}")
            # Fall back to system open command
            subprocess.run(["open", midi_path])
        
    except FileNotFoundError:
        print("⚠️ FluidSynth not found, opening with system default...")
        subprocess.run(["open", midi_path])

def play_midi_linux(midi_path: str, soundfont: str = None):
    """Play MIDI on Linux using FluidSynth or aplaymidi."""
    # Try FluidSynth first
    try:
        if soundfont and Path(soundfont).exists():
            cmd = ["fluidsynth", "-qi", soundfont, midi_path]
        else:
            cmd = ["fluidsynth", "-qi", midi_path]
        
        print(f"🎵 Playing {midi_path} with FluidSynth...")
        subprocess.run(cmd)
        return
    except FileNotFoundError:
        pass
    
    # Try aplaymidi
    try:
        print(f"🎵 Playing {midi_path} with aplaymidi...")
        subprocess.run(["aplaymidi", midi_path])
        return
    except FileNotFoundError:
        pass
    
    # Fall back to xdg-open
    print("⚠️ No MIDI player found, opening with system default...")
    subprocess.run(["xdg-open", midi_path])

def play_midi_windows(midi_path: str):
    """Play MIDI on Windows."""
    print(f"🎵 Opening {midi_path} with system default...")
    os.startfile(midi_path)

def play_midi(midi_path: str, soundfont: str = None):
    """Cross-platform MIDI playback."""
    if not Path(midi_path).exists():
        print(f"❌ MIDI file not found: {midi_path}")
        return False
    
    system = platform.system()
    
    if system == "Darwin":  # macOS
        play_midi_mac(midi_path, soundfont)
    elif system == "Linux":
        play_midi_linux(midi_path, soundfont)
    elif system == "Windows":
        play_midi_windows(midi_path)
    else:
        print(f"⚠️ Unsupported platform: {system}")
        return False
    
    return True

def rapid_iteration_workflow(base_midi: str, tenant: str = "demo"):
    """
    Rapid iteration workflow for testing rule changes.
    """
    print("🚀 SERP Radio Rapid Iteration Mode")
    print("=" * 50)
    print("Make changes to config/metric_to_label.yaml, then press ENTER to test...")
    print("Type 'quit' to exit")
    
    iteration = 1
    
    while True:
        try:
            user_input = input(f"\n[Iteration {iteration}] Press ENTER to generate & play (or 'quit'): ").strip()
            
            if user_input.lower() in ['quit', 'q', 'exit']:
                break
            
            # Generate new output
            output_path = f"/tmp/rapid_test_{iteration}.mid"
            
            print(f"🔄 Generating iteration {iteration}...")
            cmd = [
                sys.executable, "cli.py",
                "--input", base_midi,
                "--output", output_path,
                "--source", "demo",
                "--tenant", f"{tenant}_{iteration}",
                "--demo",
                "--use-training"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Generated: {output_path}")
                
                # Find and use soundfont
                soundfont = find_soundfont()
                if soundfont:
                    print(f"🎼 Using SoundFont: {soundfont}")
                
                # Play the result
                play_midi(output_path, soundfont)
                
            else:
                print(f"❌ Generation failed:")
                print(result.stderr)
            
            iteration += 1
            
        except KeyboardInterrupt:
            print("\n👋 Exiting rapid iteration mode...")
            break

def main():
    """CLI entry point for MIDI playback."""
    parser = argparse.ArgumentParser(description="Play SERP Radio MIDI files")
    parser.add_argument("midi_file", nargs="?", help="MIDI file to play")
    parser.add_argument("--soundfont", help="Path to SoundFont file")
    parser.add_argument("--rapid", action="store_true", 
                       help="Enter rapid iteration mode")
    parser.add_argument("--base-midi", default="2025-08-03T174139Z.midi",
                       help="Base MIDI file for rapid iteration")
    parser.add_argument("--tenant", default="demo",
                       help="Tenant ID for rapid iteration")
    
    args = parser.parse_args()
    
    if args.rapid:
        # Rapid iteration mode
        rapid_iteration_workflow(args.base_midi, args.tenant)
    elif args.midi_file:
        # Single file playback
        soundfont = args.soundfont or find_soundfont()
        if soundfont:
            print(f"🎼 Using SoundFont: {soundfont}")
        
        success = play_midi(args.midi_file, soundfont)
        if not success:
            sys.exit(1)
    else:
        # Find and play latest generated file
        temp_files = list(Path("/tmp").glob("serp_output_*.mid"))
        if temp_files:
            latest_file = max(temp_files, key=lambda p: p.stat().st_mtime)
            print(f"🎵 Playing latest generated file: {latest_file}")
            
            soundfont = args.soundfont or find_soundfont()
            play_midi(str(latest_file), soundfont)
        else:
            print("❌ No MIDI files found. Use --help for usage.")
            sys.exit(1)

if __name__ == "__main__":
    main()