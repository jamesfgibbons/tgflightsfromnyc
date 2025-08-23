#!/usr/bin/env python3
import sys, pathlib

try:
    import soundfile as sf
    import pyloudnorm as pyln
    import numpy as np
except ImportError:
    print("❌ Missing audio processing dependencies. Install with: pip install soundfile pyloudnorm")
    sys.exit(1)

target_lufs = -16.0
true_peak_limit = -1.0  # dBTP

bad = 0
for f in map(pathlib.Path, sys.argv[1:]):
    if not f.exists():
        print(f"❌ {f.name}: file not found")
        bad += 1
        continue
        
    try:
        data, sr = sf.read(f)
        if data.ndim > 1: data = data.mean(axis=1)  # mono sum for measurement
        meter = pyln.Meter(sr)
        loudness = meter.integrated_loudness(data)
        true_peak = 20*np.log10(np.max(np.abs(data))+1e-12)

        flags = []
        if loudness > target_lufs + 1.0: flags.append(f"too loud ({loudness:.1f} LUFS)")
        if true_peak > true_peak_limit:  flags.append(f"peaks {true_peak:.1f} dBTP")

        if flags:
            print(f"❌ {f.name}: " + ", ".join(flags)); bad += 1
        else:
            print(f"✅ {f.name}: {loudness:.1f} LUFS, peak {true_peak:.1f} dBTP")
    except Exception as e:
        print(f"❌ {f.name}: error reading audio - {e}")
        bad += 1

sys.exit(1 if bad else 0)