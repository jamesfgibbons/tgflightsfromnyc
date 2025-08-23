"""
Generate default earcon MIDI files for SERP Radio.
"""

import mido
from pathlib import Path


def create_fanfare_positive():
    """Create positive fanfare earcon."""
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    # C major triad ascent (C-E-G-C)
    notes = [60, 64, 67, 72]  # C4, E4, G4, C5
    velocity = 80
    duration = 120  # Quarter note at 120 BPM
    
    track.append(mido.MetaMessage('set_tempo', tempo=500000, time=0))  # 120 BPM
    
    time_offset = 0
    for note in notes:
        track.append(mido.Message('note_on', channel=0, note=note, velocity=velocity, time=time_offset))
        track.append(mido.Message('note_off', channel=0, note=note, velocity=0, time=duration))
        time_offset = 0
    
    return mid


def create_hit_negative():
    """Create negative impact earcon."""
    mid = mido.MidiFile(ticks_per_beat=480)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    
    # Dissonant chord (C-Db-G) with decay
    notes = [48, 49, 55]  # C3, Db3, G3
    velocity = 90
    duration = 240  # Half note
    
    track.append(mido.MetaMessage('set_tempo', tempo=500000, time=0))  # 120 BPM
    
    # Play all notes simultaneously
    for i, note in enumerate(notes):
        track.append(mido.Message('note_on', channel=0, note=note, velocity=velocity, time=0 if i > 0 else 0))
    
    # Release all notes
    for note in notes:
        track.append(mido.Message('note_off', channel=0, note=note, velocity=0, time=duration if note == notes[0] else 0))
    
    return mid


def main():
    """Generate earcon MIDI files."""
    soundpacks_dir = Path(__file__).parent
    
    # Generate positive fanfare
    fanfare = create_fanfare_positive()
    fanfare_path = soundpacks_dir / "fanfare_pos.mid"
    fanfare.save(fanfare_path)
    print(f"Generated: {fanfare_path}")
    
    # Generate negative hit
    hit = create_hit_negative()
    hit_path = soundpacks_dir / "hit_neg.mid"
    hit.save(hit_path)
    print(f"Generated: {hit_path}")


if __name__ == "__main__":
    main()