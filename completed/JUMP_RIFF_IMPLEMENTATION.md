# Jump Riff Implementation - Full 4-Bar MIDI Playback

This document describes the complete implementation of the Jump Riff feature that replaces the simple bass loop with a full 4-bar polyphonic riff with dynamic musical grading.

## Overview

The Jump Riff feature transforms SerpRadio from a simple metronome-like experience into a mini-studio mix that dynamically responds to your SEO performance metrics.

## Features Implemented

### 🎹 MIDI-Based Polyphonic Playback
- Loads `jump_theme.mid` (4-bar Van Halen style riff)
- Uses Tone.js PolySynth for rich, layered sound
- Graceful fallback to bass loop if MIDI loading fails

### 🎵 Dynamic Musical Parameters
- **Transpose**: Based on average ranking (better ranks = higher pitch)
- **Tempo**: Driven by click deltas (more clicks = faster tempo)
- **Velocity**: Modulated by top-3 keyword gains (more top-3s = louder/more energetic)

### 🎸 CTR Jump Detection
- Automatically detects CTR increases ≥ 0.5%
- Triggers guitar fill overlay for excitement
- Synthetic fallback arpeggio if sample missing

### 🌐 Infrastructure
- Nginx configuration for MIDI file serving
- Proper MIME types and caching headers
- CORS support for cross-origin requests

## File Structure

```
widget/
├── midi/
│   ├── README.md
│   └── jump_theme.mid          # 4-bar MIDI riff (upload manually)
├── samples/
│   ├── README.md
│   ├── guitar_fill.wav         # CTR jump solo (optional)
│   └── [existing samples...]
└── player.js                   # Enhanced with MIDI support

src/
└── note_streamer.py            # Delta calculations and enhanced motif

infra/nginx/
└── serpradio_midi.conf         # MIDI serving configuration

scripts/
└── deploy-jump-riff.sh         # Complete deployment script
```

## Technical Implementation

### Client-Side (player.js)
1. **Enhanced motif object**: Now includes transpose, velocity, and tempo
2. **MIDI loading**: `loadJumpMidi()` function loads and parses MIDI files
3. **Polyphonic synthesis**: PolySynth with sawtooth oscillators for rock sound
4. **Real-time parameter updates**: Motif messages update all parameters dynamically
5. **CTR jump detection**: Triggers guitar_fill sample on significant improvements

### Server-Side (note_streamer.py)
1. **Delta calculations**: Computes top3_delta and ctr_delta between periods
2. **Enhanced motif messages**: Includes all parameters needed for full riff control
3. **Period-to-period tracking**: Maintains state for accurate delta calculations

### Infrastructure
1. **MIDI serving**: Nginx configuration with proper MIME types
2. **Sample management**: Enhanced fallback system for missing audio files
3. **Deployment automation**: Complete script for production deployment

## Usage

### Development
```bash
# Test locally (no server changes needed)
cd widget
# Place jump_theme.mid in midi/ directory
# Open widget/index.html and test with CSV uploads
```

### Production Deployment
```bash
# Deploy everything to production server
./scripts/deploy-jump-riff.sh root@your-server-ip

# Manual MIDI upload if needed
scp widget/midi/jump_theme.mid root@your-server:/opt/serpradio/widget/midi/
```

## How It Sounds

### Before (Simple Bass Loop)
- Single bass note per beat
- Fixed tempo and pitch
- Metronome-like experience

### After (Jump Riff)
- Full 4-bar polyphonic riff
- Dynamic key changes based on rank performance
- Tempo responds to click improvements
- Velocity modulates with top-3 keyword gains
- Guitar solos trigger on major CTR jumps
- Studio-quality mix with overlays

## Musical Mapping

| Metric | Musical Parameter | Effect |
|--------|------------------|--------|
| Average Rank | Transpose | Better ranks = higher pitch |
| Click Delta | Tempo | More clicks = faster tempo |
| Top-3 Delta | Velocity | More top-3s = louder/more energetic |
| CTR Jump ≥0.5% | Guitar Fill | Solo overlay for excitement |

## Expected Experience

1. **Period 1**: Jump riff plays at 120 BPM, -2 semitones, normal velocity
2. **Period 2**: Tempo increases to 124 BPM if clicks improved, key might shift with rank changes
3. **Big improvement**: Velocity increases and guitar fill triggers for major CTR jumps
4. **Continuous evolution**: Each period brings new musical character based on performance

## Fallbacks & Robustness

- **No MIDI file**: Falls back to existing bass loop
- **No guitar_fill.wav**: Uses synthetic arpeggio
- **Network issues**: All samples have synthetic fallbacks
- **Browser compatibility**: Graceful degradation for older browsers

## Next Steps

1. Upload a 4-bar `jump_theme.mid` file to `widget/midi/`
2. Optionally add `guitar_fill.wav` to `widget/samples/`
3. Test with your time-series CSV data
4. Deploy to production with the provided script

The result is a dynamic, engaging audio experience that makes SEO data analysis feel like conducting a live band! 🎵 