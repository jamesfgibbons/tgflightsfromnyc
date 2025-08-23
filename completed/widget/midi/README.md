# MIDI Assets for SerpRadio

This directory contains MIDI files used for the full riff playback feature.

## Files

- `jump_theme.mid` - 4-bar Van Halen "Jump" style guitar/keys riff
  - Used as the main musical motif instead of simple bass loop
  - Dynamically transposed based on average rank
  - Tempo adjusted based on click deltas
  - Velocity controlled by top-3 keyword deltas

## Usage

The MIDI files are served via nginx and loaded by the client-side player.js using Tone.js MIDI parsing. Each period in time-series playback triggers the full riff with appropriate musical parameters based on performance metrics.

## Adding New MIDI Files

1. Ensure files are short (4 bars or less) and royalty-free
2. Single track MIDI files work best
3. Place in this directory and update nginx config if needed
4. Update player.js to reference new files 