# Audio Samples for SerpRadio

This directory contains audio samples used for overlay effects during playback.

## Current Samples

### Core Samples
- `video_cymbal.wav` - Cymbal crash for video SERP features
- `cash_register.wav` - Ka-ching sound for ad slots and monetization features
- `snare.wav` - Snare hit for shopping pack results
- `jump_bass.wav` - Van Halen style bass stab for brand wins

### New Samples (Jump Riff Feature)
- `guitar_fill.wav` - Guitar solo fill for significant CTR jumps (≥0.5%)
  - Triggered when CTR increases by 0.5 percentage points or more
  - Adds excitement to major performance improvements
  - Falls back to synthetic guitar arpeggio if file missing

## Fallback Behavior

All samples have synthetic fallbacks that trigger if the audio files are missing:
- `video_cymbal.wav` → High C6 note
- `cash_register.wav` → Sharp G5 note  
- `snare.wav` → Punchy F4 note
- `jump_bass.wav` → Low C2 note
- `guitar_fill.wav` → E3-G3-B3-E4 arpeggio

## Adding New Samples

1. Place WAV files in this directory
2. Update `initSamplePlayers()` in player.js
3. Add fallback case in `createSynthFallback()`
4. Reference by filename in server-side code

Keep samples short (< 2 seconds) and royalty-free. 