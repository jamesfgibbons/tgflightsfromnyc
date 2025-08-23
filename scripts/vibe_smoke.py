#!/usr/bin/env python
"""
Simple smoke script for Vibe Engine endpoints.
Tests motif upload and palette generate. Attempts screenshot if SMOKE_SCREENSHOT is set.
"""
import os
import sys
import time
import json
import requests

BASE = os.getenv("BASE", "http://localhost:8000")


def post(path: str, **kwargs):
    url = f"{BASE}{path}"
    r = requests.post(url, timeout=60, **kwargs)
    return r


def do_motif():
    events = []
    # Short C major arpeggio over ~2 seconds
    t = 0.0
    for n in [60, 64, 67, 72]:
        events.append({"t": t, "on": True, "note": n, "vel": 96, "ch": 0})
        t += 0.4
        events.append({"t": t, "on": False, "note": n, "vel": 0, "ch": 0})
    body = {
        "title": "Smoke Motif",
        "bpm": 112,
        "key_center": "C",
        "bars": 2,
        "events": events,
    }
    r = post("/api/vibe/motif", json=body)
    print("motif status:", r.status_code)
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)


def do_generate():
    body = {
        "palette_slug": "caribbean_kokomo",
        "sound_pack": "Synthwave",
        "total_bars": 16,
        "tempo_hint": 112,
        "momentum_bands": [
            {"t0": 0, "t1": 8, "label": "positive", "score": 0.6},
            {"t0": 8, "t1": 16, "label": "neutral", "score": 0.5},
        ],
    }
    r = post("/api/vibe/generate", json=body)
    print("generate status:", r.status_code)
    try:
        print(json.dumps(r.json(), indent=2))
    except Exception:
        print(r.text)


def do_screenshot():
    path = os.getenv("SMOKE_SCREENSHOT")
    if not path or not os.path.exists(path):
        print("(screenshot skipped; set SMOKE_SCREENSHOT to a PNG path)")
        return
    with open(path, "rb") as f:
        files = {"file": (os.path.basename(path), f, "image/png")}
        r = post("/api/vibe/screenshot", files=files)
        print("screenshot status:", r.status_code)
        try:
            print(json.dumps(r.json(), indent=2))
        except Exception:
            print(r.text)


if __name__ == "__main__":
    do_motif()
    do_generate()
    do_screenshot()

