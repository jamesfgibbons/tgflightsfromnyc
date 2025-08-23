#!/usr/bin/env python3
import json, sys, pathlib

REQ_TRACK_FIELDS = {"route","price","qtile","volatility","novel","audio_url","art_url","hints"}

def fail(msg): print(f"❌ {msg}"); sys.exit(1)
def ok(msg):   print(f"✅ {msg}")

p = pathlib.Path(sys.argv[1])
j = json.loads(p.read_text())

for key in ["run_sha","generated_at","tracks"]:
    if key not in j: fail(f"Missing top-level key: {key}")
ok("Top-level keys present")

tracks = j["tracks"]
if not tracks: fail("No tracks in catalog")

bad = []
for i,t in enumerate(tracks):
    missing = REQ_TRACK_FIELDS - t.keys()
    if missing: bad.append((i, missing))
if bad:
    for i,miss in bad: print(f"Track {i} missing: {sorted(miss)}")
    fail("Schema errors in catalog")
ok(f"All {len(tracks)} tracks match schema")

# Count unique routes
routes = {t["route"] for t in tracks}
ok(f"Unique routes: {len(routes)}")

print("🎉 Catalog validation passed")