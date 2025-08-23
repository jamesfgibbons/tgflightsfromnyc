#!/usr/bin/env python3
import json, sys, pathlib, urllib.parse

catalog = pathlib.Path(sys.argv[1])
audio_dir = pathlib.Path(sys.argv[2])  # local staging if present

j = json.loads(catalog.read_text())
urls = [t["audio_url"] for t in j["tracks"]]
filenames = {pathlib.Path(urllib.parse.urlparse(u).path).name for u in urls}

missing = []
for u in filenames:
    if not (audio_dir / u).exists():
        missing.append(u)

if missing:
    print("❌ Missing audio files referenced in catalog:")
    for m in missing: print("  -", m)
    sys.exit(2)

print(f"✅ All {len(filenames)} audio files exist locally")