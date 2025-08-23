"""
Helpers for Vibe Engine: OpenAI Vision OCR for screenshots, Spotify audio features,
and MIDI event conversion into SMF bytes.
"""
from __future__ import annotations
import base64
import io
import json
import os
import time
from typing import Any, Dict, List

import requests
from midiutil import MIDIFile

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore


def _openai_client():
    if OpenAI is None:
        raise RuntimeError("openai package not installed")
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")
    return OpenAI(api_key=key)


def extract_track_from_screenshot(img_bytes: bytes) -> Dict[str, Any]:
    """OCR + extraction via OpenAI Vision. Returns dict with artist, track, confidence, ocr_text.

    This is best-effort; caller decides how to handle low confidence.
    """
    client = _openai_client()
    b64 = base64.b64encode(img_bytes).decode()
    system = (
        "You are an OCR+music assistant. Extract {artist, track} from a music-player "
        "screenshot (e.g., Spotify). Return strict JSON with fields: artist, track, "
        "confidence (0..1), ocr_text."
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        temperature=0.1,
        messages=[
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Extract track & artist"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
                ],
            },
        ],
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except Exception:
        return {"artist": None, "track": None, "confidence": 0.0, "ocr_text": ""}


_spotify_cache: Dict[str, Any] = {"token": None, "exp": 0.0}


def _spotify_token() -> str:
    now = time.time()
    tok = _spotify_cache.get("token")
    exp = float(_spotify_cache.get("exp") or 0)
    if tok and now < exp - 60:
        return tok
    cid = os.getenv("SPOTIFY_CLIENT_ID")
    sec = os.getenv("SPOTIFY_CLIENT_SECRET")
    if not cid or not sec:
        raise RuntimeError("SPOTIFY_CLIENT_ID/SECRET not set")
    auth = base64.b64encode(f"{cid}:{sec}".encode()).decode()
    r = requests.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "client_credentials"},
        headers={"Authorization": f"Basic {auth}"},
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    _spotify_cache["token"] = data["access_token"]
    _spotify_cache["exp"] = now + 3500
    return _spotify_cache["token"]


def fetch_spotify_audio_features(track: str, artist: str) -> Dict[str, Any]:
    tok = _spotify_token()
    q = requests.get(
        "https://api.spotify.com/v1/search",
        params={"q": f"track:{track} artist:{artist}", "type": "track", "limit": 1},
        headers={"Authorization": f"Bearer {tok}"},
        timeout=20,
    )
    q.raise_for_status()
    items = q.json().get("tracks", {}).get("items", [])
    if not items:
        return {"track_id": None}
    tid = items[0]["id"]
    feats = requests.get(
        f"https://api.spotify.com/v1/audio-features/{tid}",
        headers={"Authorization": f"Bearer {tok}"},
        timeout=20,
    ).json()
    return {
        "track_id": tid,
        "tempo": feats.get("tempo"),
        "key": feats.get("key"),
        "mode": feats.get("mode"),
        "energy": feats.get("energy"),
        "valence": feats.get("valence"),
        "danceability": feats.get("danceability"),
        "acousticness": feats.get("acousticness"),
        "instrumentalness": feats.get("instrumentalness"),
        "liveness": feats.get("liveness"),
        "speechiness": feats.get("speechiness"),
    }


def midi_events_to_midi_bytes(events: List[Dict[str, Any]], bpm: int = 112) -> bytes:
    """Convert front-end captured MIDI event list into an SMF (MIDI) bytes blob.

    Event format: {t: seconds, on: bool, note: int, vel: int, ch: int}
    """
    mf = MIDIFile(1)
    mf.addTempo(0, 0, bpm)
    on_notes: Dict[tuple[int, int], tuple[float, int]] = {}

    for e in sorted(events, key=lambda x: float(x.get("t", 0.0))):
        t = float(e.get("t", 0.0))
        ch = int(e.get("ch", 0))
        note = int(e.get("note", 60))
        vel = int(e.get("vel", 90))
        on = bool(e.get("on", True))
        key = (ch, note)
        if on:
            on_notes[key] = (t, vel)
        else:
            t_on, v_on = on_notes.pop(key, (t, vel))
            dur = max(0.05, t - t_on)
            mf.addNote(0, ch, note, t_on, dur, v_on)

    buf = io.BytesIO()
    mf.writeFile(buf)
    return buf.getvalue()


# --- LLM feature inference from artist/title (no Spotify required) ---
import json as _json


def infer_music_features_llm(artist: str, title: str) -> Dict[str, Any]:
    """
    Infer tempo/valence/energy/key/mode + tags from just artist/title via OpenAI.
    Returns a compact feature dict the vibe engine can consume.
    """
    client = _openai_client()

    system = (
        "You are a musicologist. Given artist/title, estimate rough musical "
        "features as JSON ONLY: {tempo_bpm, valence_0_1, energy_0_1, "
        "mode: 'major'|'minor', key_center (like 'C','G','Am'), tags: []}. "
        "Be conservative and avoid extreme values unless iconic."
    )
    user = f"artist: {artist}\ntitle: {title}"

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    try:
        data = _json.loads(resp.choices[0].message.content)
        out = {
            "tempo_bpm": max(60, min(180, int(data.get("tempo_bpm", 112)))),
            "valence_0_1": max(0.0, min(1.0, float(data.get("valence_0_1", 0.6)))),
            "energy_0_1": max(0.0, min(1.0, float(data.get("energy_0_1", 0.6)))),
            "mode": data.get("mode", "major"),
            "key_center": data.get("key_center", "C"),
            "tags": data.get("tags", []),
        }
        return out
    except Exception:
        # Safe fallback
        return {
            "tempo_bpm": 112,
            "valence_0_1": 0.6,
            "energy_0_1": 0.6,
            "mode": "major",
            "key_center": "C",
            "tags": [],
        }


import yaml as _yaml


def choose_palette_from_rules(artist: str, title: str) -> Optional[str]:
    """Load simple keyword rules and choose a palette slug. Returns slug or None."""
    rules_path = os.getenv("VIBE_RULES_PATH", "config/vibe_rules.yaml")
    if not os.path.exists(rules_path):
        return None
    try:
        with open(rules_path, "r") as f:
            rules = _yaml.safe_load(f) or {}
    except Exception:
        return None

    text = f"{artist} {title}".lower()
    for rule in rules.get("keyword_map", []):
        keywords = [str(k).lower() for k in rule.get("keywords", [])]
        if any(k in text for k in keywords):
            slug = rule.get("palette_slug")
            if isinstance(slug, str) and slug:
                return slug
    return None


def normalize_features(feats: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize mixed-source features (Spotify or LLM) to canonical keys.

    Expected output keys:
      tempo_bpm:int, valence_0_1:float, energy_0_1:float,
      mode:"major"|"minor", key_center:str, tags:list
    """
    # Mode normalization
    mode_raw = feats.get("mode")
    if isinstance(mode_raw, int):
        mode = "major" if int(mode_raw) == 1 else "minor"
    else:
        mode = str(mode_raw or "major").lower()
        if mode not in ("major", "minor"):
            mode = "major"

    # Tempo
    tempo = feats.get("tempo_bpm") or feats.get("tempo") or 112
    try:
        tempo = int(tempo)
    except Exception:
        tempo = 112

    # Valence/Energy
    def _f(x: Any, default: float) -> float:
        try:
            return float(x)
        except Exception:
            return default

    val = _f(feats.get("valence_0_1") or feats.get("valence"), 0.6)
    enr = _f(feats.get("energy_0_1") or feats.get("energy"), 0.6)
    val = max(0.0, min(1.0, val))
    enr = max(0.0, min(1.0, enr))

    # Key center (accept numeric Spotify key or string)
    key_center = feats.get("key_center")
    if not key_center:
        key_num = feats.get("key")
        if isinstance(key_num, (int, float)):
            names = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
            try:
                key_center = names[int(key_num) % 12]
            except Exception:
                key_center = "C"
        else:
            key_center = "C"

    return {
        "tempo_bpm": tempo,
        "valence_0_1": round(val, 3),
        "energy_0_1": round(enr, 3),
        "mode": mode,
        "key_center": str(key_center),
        "tags": feats.get("tags", []),
    }
