# Assets Directory

This directory contains audio assets for SERP Loop Radio.

## Required Files

### Soundfont (Required for audio rendering)
- **nice_gm.sf2** - General MIDI soundfont for FluidSynth
- Download from: https://musical-artifacts.com/artifacts/618
- Or use system soundfont from `/usr/share/sounds/sf2/`

### Bass Riff (Optional)
- **jump_riff.mid** - Pre-recorded bass riff in C major, 112 BPM, 8 bars
- Triggered when brand ranks in top 3 positions
- Should be in 4/4 time signature

### Audio Samples (Optional)
- **intro.mp3** - Intro sound for audio reports
- **outro.mp3** - Outro sound for audio reports

## Automatic Download

The Docker image will automatically download a free soundfont if none is found.

For local development, you can download manually:

```bash
# Download FluidR3 soundfont
wget -O assets/FluidR3_GM.sf2 "https://archive.org/download/FluidR3Gm/FluidR3%20GM.sf2"
```

## Creating Custom Bass Riff

To create your own bass riff:

1. Create MIDI file in your DAW
2. Use 4/4 time signature at 112 BPM
3. Keep to 8 bars maximum
4. Use root note C (MIDI note 60)
5. Save as `assets/jump_riff.mid`

The system will automatically transpose to the current key and trigger when brand performance meets criteria. 