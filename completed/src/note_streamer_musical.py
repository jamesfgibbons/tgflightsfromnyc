#!/usr/bin/env python3
"""
Musical Note Streamer with Van Halen "Jump" Motif
Real-time melody morphing based on SERP data trends.
"""

import os
import json
import asyncio
import logging
import time
from typing import Dict, List, Optional, Any
from collections import Counter

logger = logging.getLogger(__name__)

# Musical motif state
motif_state = {"bars": 0, "next_emit": 0, "transpose": 0, "tempo": 120}

def scale(value, in_min, in_max, out_min, out_max):
    """Scale a value from one range to another."""
    return ((value - in_min) * (out_max - out_min) / (in_max - in_min)) + out_min

def clamp(value, min_val, max_val):
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))

async def emit_motif(ws, rows: List[Dict], client_domain: str):
    """Emit motif updates based on streaming data trends."""
    if not rows:
        return
    
    # Analyze brand performance
    brand_hits = [r for r in rows if client_domain and client_domain.lower() in r.get("domain", "").lower()]
    
    if brand_hits:
        # Calculate average rank (lower is better)
        avg_rank = sum(r.get("rank", 50) for r in brand_hits) / len(brand_hits)
        # Transpose: rank 1 = +7 semitones, rank 100 = -5 semitones
        transpose = round(scale(avg_rank, 1, 100, 7, -5))
        
        # Calculate momentum from rank deltas
        deltas = [r.get("rank_delta", 0) for r in brand_hits]
        avg_delta = sum(deltas) / len(deltas) if deltas else 0
        # Tempo: gains = faster, losses = slower
        tempo = clamp(120 - avg_delta * 5, 90, 140)
    else:
        # No brand hits - neutral settings
        transpose = 0
        tempo = 120
    
    # Check for AI Overview threats (AI without brand presence)
    recent_rows = rows[-10:] if len(rows) > 10 else rows
    ai_steal = any(r.get("ai_overview", False) and not (client_domain and client_domain.lower() in r.get("domain", "").lower()) 
                   for r in recent_rows)
    
    # Check for competitor threats (competitors ranking significantly higher)
    competitor_ahead = False
    if brand_hits and client_domain:
        min_brand_rank = min(r.get("rank", 100) for r in brand_hits)
        competitors = [r for r in recent_rows if not (client_domain.lower() in r.get("domain", "").lower())]
        if competitors:
            min_competitor_rank = min(r.get("rank", 100) for r in competitors)
            competitor_ahead = min_competitor_rank < min_brand_rank - 2
    
    # Filter cutoff for brightness
    cutoff = 1000 if ai_steal else 400
    
    motif_msg = {
        "type": "motif",
        "transpose": transpose,
        "tempo": int(tempo),
        "cutoff": cutoff,
        "minor": competitor_ahead,
        "ai_steal": ai_steal,
        "brand_avg_rank": round(sum(r.get("rank", 50) for r in brand_hits) / len(brand_hits), 1) if brand_hits else None,
        "momentum": round(avg_delta, 1) if brand_hits else 0
    }
    
    logger.info(f"Motif update: transpose={transpose}, tempo={tempo}, ai_steal={ai_steal}, competitor_ahead={competitor_ahead}")
    
    await ws.send_json(motif_msg)
    
    # Update global state
    motif_state["transpose"] = transpose
    motif_state["tempo"] = tempo

async def emit_scorecard_overture(ws, rows: List[Dict], client_domain: str):
    """Play one bar per domain ranked by share - the scorecard overture."""
    if not rows:
        return
    
    # Calculate domain shares
    domain_counter = Counter(r.get("domain", "") for r in rows)
    total_results = len(rows)
    
    # Get top domains by share
    top_domains = []
    for domain, count in domain_counter.most_common(5):
        if domain:
            share = count / total_results
            top_domains.append({
                "domain": domain,
                "count": count,
                "share": share,
                "is_client": client_domain and client_domain.lower() in domain.lower()
            })
    
    if not top_domains:
        return
    
    # Determine if client won (>= 40% share)
    client_share = 0
    for item in top_domains:
        if item["is_client"]:
            client_share = item["share"]
            break
    
    client_won = client_share >= 0.4
    
    # Send overture start message
    await ws.send_json({
        "type": "overture_start",
        "data": {
            "message": "🎵 Scorecard overture - one chord per domain leader",
            "client_won": client_won,
            "client_share": round(client_share * 100, 1)
        }
    })
    
    await asyncio.sleep(1.0)
    
    # Play chords for each domain
    base_notes = ["C4", "E4", "G4", "B4", "D5"]  # Major chord progression
    
    for i, item in enumerate(top_domains):
        # Calculate chord properties
        note = base_notes[i % len(base_notes)]
        velocity = int(40 + item["share"] * 80)  # Volume based on share
        pan = 0.0 if item["is_client"] else (-0.3 if i % 2 == 0 else 0.3)  # Client center, others L/R
        
        # Use minor chord if client didn't win and this is client
        chord_type = "minor" if item["is_client"] and not client_won else "major"
        
        chord_msg = {
            "type": "overture_chord",
            "data": {
                "note": note,
                "velocity": velocity,
                "pan": pan,
                "duration": 2.0,
                "chord_type": chord_type,
                "domain": item["domain"],
                "share": round(item["share"] * 100, 1),
                "is_client": item["is_client"]
            }
        }
        
        await ws.send_json(chord_msg)
        await asyncio.sleep(0.8)  # Stagger chords
    
    # Final flourish if client won
    if client_won:
        await asyncio.sleep(0.5)
        await ws.send_json({
            "type": "victory_flourish",
            "data": {
                "message": "🎸 Van Halen victory riff!",
                "client_share": round(client_share * 100, 1)
            }
        })

def map_row_to_musical_note(row: Dict, patch_map: Dict, client_domain: str = None) -> Dict:
    """Convert SERP row to musical note with Van Halen motif elements."""
    import random
    
    # Base note mapping
    domain = row.get('domain', '').lower()
    rank = row.get('rank', 5)
    
    # Van Halen Jump bass line notes (C-C-G-C pattern)
    jump_notes = ["C3", "C3", "G2", "C3"]
    base_note = jump_notes[rank % 4]
    
    # Check if this is a brand hit
    is_brand_hit = client_domain and client_domain.lower() in domain
    
    # Calculate frequency and musical properties
    base_freq = 440
    frequency = base_freq * (2 ** ((10 - rank) / 12))
    
    # Apply patch modifications
    patch = None
    for key in patch_map:
        if key in domain:
            patch = patch_map[key]
            break
    if not patch:
        patch = patch_map.get('default', {"waveform": "sawtooth", "amp_mod": 1.0})
    
    frequency *= patch.get('amp_mod', 1.0)
    
    # Duration and amplitude
    duration = random.uniform(0.3, 0.8)
    amplitude = random.uniform(0.2, 0.5) * patch.get('amp_mod', 1.0)
    amplitude = min(amplitude, 0.6)
    velocity = int(amplitude * 127)
    
    # Build the note object
    note = {
        "frequency": frequency,
        "duration": duration,
        "amplitude": amplitude,
        "velocity": velocity,
        "waveform": patch["waveform"],
        "keyword": row.get('keyword', ''),
        "domain": row.get('domain', ''),
        "rank": rank,
        "note": base_note,
        "is_brand_hit": is_brand_hit,
        "amp_mod": patch.get('amp_mod', 1.0),
        "transpose": motif_state.get("transpose", 0),
        "pan": 0.0,  # Center for main melody
        "channel": "center"
    }
    
    # Add special effects based on SERP features
    
    # Brand win - Van Halen stab for top 3 brand hits
    if is_brand_hit and rank <= 3:
        note["overlay"] = "jump_bass_stab"
        note["badge"] = "🏆"
        note["amp_mod"] *= 1.5
        note["duration"] *= 1.3
        note["waveform"] = "sawtooth"  # Aggressive sound
    
    # Rank drop - lower pitch and volume
    rank_delta = row.get("rank_delta", 0)
    if rank_delta <= -3:
        note["transpose"] -= 3
        note["velocity"] = int(note["velocity"] * 0.6)
        note["badge"] = "↓"
        note["amp_mod"] *= 0.7
    
    # AI overview without brand - filter sweep and bell overlay
    if row.get("ai_overview") and not is_brand_hit:
        note["filter_sweep"] = True
        note["overlay"] = "bell_warning"
        note["badge"] = "🤖"
        note["pan"] = 0.6  # Right pan
        note["waveform"] = "triangle"
        note["channel"] = "right"
    
    # Shopping pack with brand - hi-hat shuffle
    if row.get("rich_snippet_type") == "shopping_pack" and is_brand_hit:
        note["overlay"] = "hihat_shuffle"
        note["badge"] = "🛒💰"
        note["amp_mod"] *= 1.2
    
    # Video results - cymbal overlay
    if row.get("rich_snippet_type") == "video":
        note["overlay"] = "video_cymbal"
        note["badge"] = "🎥"
        note["amp_mod"] *= 1.1
    
    # Ads slots - cash register
    if row.get("ads_slot") in ("top", "shopping"):
        note["overlay"] = "cash_register"
        note["badge"] = "💰"
        note["amp_mod"] *= 1.15
    
    # Competitor notes (quieter, left channel)
    if not is_brand_hit and rank <= 5:
        note["velocity"] = int(note["velocity"] * 0.3)  # 20dB quieter
        note["pan"] = -0.3  # Left pan
        note["channel"] = "left"
        note["badge"] = note.get("badge", "") + "👥"
    
    return note

async def stream_session_musical(ws, session_id: str, skin: str = "arena_rock"):
    """Stream session with musical Van Halen motif."""
    from .session import get_session
    
    rows = get_session(session_id)
    if not rows:
        await ws.send_json({"type": "error", "data": {"message": "Session not found"}})
        return
    
    client_domain = os.getenv("CLIENT_DOMAIN", "")
    streamed = []
    
    # Get skin patch map
    from .api import SKINS
    patch_map = SKINS.get(skin, SKINS["arena_rock"])["patch_map"]
    
    logger.info(f"Starting musical stream for {len(rows)} rows with client domain: {client_domain}")
    
    # Send initial motif setup
    await ws.send_json({
        "type": "motif_init",
        "data": {
            "client_domain": client_domain,
            "bass_pattern": ["C3", "C3", "G2", "C3"],
            "initial_tempo": 120,
            "message": "🎸 Van Halen Jump motif initialized"
        }
    })
    
    # Reset motif state
    motif_state["bars"] = 0
    
    # Stream notes with motif updates
    for i, row in enumerate(rows):
        streamed.append(row)
        
        # Map to musical note
        note = map_row_to_musical_note(row, patch_map, client_domain)
        
        # Send note event
        note_event = {
            "type": "musical_note",
            "data": note,
            "index": i,
            "total": len(rows)
        }
        
        await ws.send_json(note_event)
        
        # Update motif every 4 bars
        motif_state["bars"] += 1
        if motif_state["bars"] >= 4:
            motif_state["bars"] = 0
            await emit_motif(ws, streamed, client_domain)
        
        await asyncio.sleep(0.25)
    
    # Play scorecard overture
    await emit_scorecard_overture(ws, rows, client_domain)
    
    # Send completion
    await ws.send_json({
        "type": "complete",
        "data": {"message": "🎵 Musical stream complete - Van Halen style!"}
    }) 