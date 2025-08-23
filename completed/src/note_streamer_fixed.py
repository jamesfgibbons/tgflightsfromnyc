import asyncio
import json
import os
import session
try:
    import scorecard
except ImportError:
    scorecard = None

# Musical skin configurations
SKINS = {
    "arena_rock": {
        "patch_map": {
            "google": {"waveform": "sawtooth", "amp_mod": 1.3},
            "youtube": {"waveform": "square", "amp_mod": 1.2},
            "amazon": {"waveform": "triangle", "amp_mod": 1.1},
            "default": {"waveform": "sawtooth", "amp_mod": 1.0}
        }
    },
    "synth_pop": {
        "patch_map": {
            "google": {"waveform": "sine", "amp_mod": 1.0},
            "youtube": {"waveform": "triangle", "amp_mod": 0.9},
            "amazon": {"waveform": "square", "amp_mod": 0.8},
            "default": {"waveform": "sine", "amp_mod": 0.7}
        }
    },
    "retro_8bit": {
        "patch_map": {
            "google": {"waveform": "square", "amp_mod": 1.2},
            "youtube": {"waveform": "sawtooth", "amp_mod": 1.1},
            "amazon": {"waveform": "triangle", "amp_mod": 1.0},
            "default": {"waveform": "square", "amp_mod": 0.9}
        }
    }
}

def map_row_to_note(row, patch_map):
    """Convert SERP row to musical note using patch mapping with brand insights."""
    import random
    
    # Base mapping (existing logic)
    note = base_mapping(row, patch_map)
    
    # Brand win - Van Halen stab for top 3 brand hits
    if row.get("brand_hit") and row["rank"] <= 3:
        note["overlay"] = "jump_bass.mid"
        note["badge"] = "🏆"
        note["amp_mod"] = note.get("amp_mod", 1.0) * 1.5  # Boost volume
        note["duration"] = note.get("duration", 0.5) * 1.3  # Longer duration
    
    # Rank drop - lower pitch and volume for poor rankings
    if row.get("rank_delta", 0) <= int(os.getenv("INSIGHT_RANK_DROP", "-3")):
        note["transpose"] = -3
        note["velocity"] = int(note.get("velocity", 80) * 0.6)
        note["badge"] = "↓"
        note["amp_mod"] = note.get("amp_mod", 1.0) * 0.7  # Reduce volume
    
    # AI overview - special patch and panning
    if row.get("ai_overview") and not row.get("brand_hit"):
        note["patch"] = 14  # Special AI patch
        note["pan"] = 0.8   # Pan right
        note["badge"] = "🤖"
        note["waveform"] = "triangle"  # Distinctive waveform for AI
    
    # Shopping pack - snare overlay
    if row.get("rich_snippet_type") == "shopping_pack":
        note["overlay"] = "snare.wav"
        note["badge"] = "🛒"
        note["amp_mod"] = note.get("amp_mod", 1.0) * 1.2  # Slightly louder

    # Video results - cymbal overlay
    if row.get("rich_snippet_type") == "video":
        note["overlay"] = "video_cymbal.wav"
        note["badge"] = "🎥"
        note["amp_mod"] = note.get("amp_mod", 1.0) * 1.1
    
    # Ads slots - cash register overlay
    if row.get("ads_slot") in ("top", "shopping"):
        note["overlay"] = "cash_register.wav"
        note["badge"] = "💰"
        note["amp_mod"] = note.get("amp_mod", 1.0) * 1.15
    
    return note

def base_mapping(row, patch_map):
    """Base note mapping logic (extracted from original map_row_to_note)."""
    import random
    
    # Get domain-specific patch or default
    domain = row.get('domain', '').lower()
    patch = None
    for key in patch_map:
        if key in domain:
            patch = patch_map[key]
            break
    if not patch:
        patch = patch_map.get('default', {"waveform": "sine", "amp_mod": 1.0})
    
    # Map rank to frequency (higher rank = lower frequency)
    rank = row.get('rank', 5)
    base_freq = 440  # A4
    frequency = base_freq * (2 ** ((10 - rank) / 12))  # Chromatic scale
    frequency *= patch.get('amp_mod', 1.0)
    
    # Generate note parameters
    duration = random.uniform(0.3, 0.8)
    amplitude = random.uniform(0.2, 0.5) * patch.get('amp_mod', 1.0)
    amplitude = min(amplitude, 0.6)  # Cap amplitude
    velocity = int(amplitude * 127)  # MIDI velocity
    
    # Note name for display
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    note = f"{note_names[rank % 12]}{4 + (rank // 12)}"
    
    return {
        "frequency": frequency,
        "duration": duration,
        "amplitude": amplitude,
        "velocity": velocity,
        "waveform": patch["waveform"],
        "keyword": row.get('keyword', ''),
        "domain": row.get('domain', ''),
        "rank": rank,
        "note": note,
        "brand_hit": row.get('brand_hit', False),
        "amp_mod": patch.get('amp_mod', 1.0),
        "transpose": 0,
        "pan": 0.5  # Center pan by default
    }

def domain_league_fallback(rows):
    """Fallback domain league function if scorecard module not available."""
    from collections import Counter
    
    # Filter to top-10 results only
    top10 = [r for r in rows if r.get("rank", 0) <= 10]
    
    if not top10:
        return []
    
    # Count domain appearances
    domain_counter = Counter(r.get("domain", "") for r in top10)
    total_appearances = len(top10)
    
    # Calculate share percentages
    league_table = []
    for domain, count in domain_counter.most_common():
        if domain:  # Skip empty domains
            share = count / total_appearances
            league_table.append({
                "domain": domain,
                "appearances": count,
                "share": share,
                "percentage": round(share * 100, 1)
            })
    
    return league_table

def generate_insights_fallback(rows):
    """Fallback insights generation if scorecard module not available."""
    insights = []
    
    if not rows:
        return ["No data available for analysis."]
    
    # Domain league analysis
    league = domain_league_fallback(rows)
    if league:
        winner = league[0]
        insights.append(f"🏆 {winner['domain']} dominates with {winner['percentage']}% share")
    
    # AI Overview impact
    ai_count = sum(1 for r in rows if r.get("ai_overview", False))
    if ai_count > 0:
        ai_percentage = (ai_count / len(rows)) * 100
        insights.append(f"🤖 AI Overview appeared in {ai_percentage:.1f}% of results")
    
    return insights[:5]  # Limit to top 5 insights

async def stream_session(ws, session_id: str, skin: str):
    """Stream notes for a session with specified skin and brand insights."""
    rows = session.get_session(session_id)
    if not rows:
        await ws.close(code=4404)
        return
    
    # Get skin configuration
    patch_map = SKINS.get(skin, SKINS["arena_rock"])["patch_map"]
    
    # Send status
    await ws.send_json({
        "type": "status",
        "data": {
            "message": f"Streaming {len(rows)} notes with {skin} skin",
            "total_notes": len(rows),
            "skin": skin
        }
    })
    
    # Stream notes with brand insights
    bars = 0
    for i, row in enumerate(rows):
        try:
            # Stream low-C drone every four bars for high brand share
            if bars % 4 == 0 and row.get("drone"):
                await ws.send_json({
                    "type": "drone_event",
                    "data": {
                        "pitch": 36,  # Low C
                        "duration": 2.0,
                        "velocity": 60,
                        "patch": 48,
                        "frequency": 65.4,  # C2
                        "waveform": "sine",
                        "amplitude": 0.3
                    }
                })
            
            # Map row to note with insights
            note = map_row_to_note(row, patch_map)
            note_event = {
                "type": "note_event",
                "data": note,
                "index": i,
                "total": len(rows)
            }
            
            await ws.send_json(note_event)
            bars += 1
            await asyncio.sleep(0.25)  # 250ms between notes
            
        except Exception as e:
            print(f"Error streaming note {i}: {e}")
            continue
    
    # --- Recap Overture ---
    if scorecard:
        league = scorecard.domain_league(rows)
        insights = scorecard.generate_recap_insights(rows)
    else:
        league = domain_league_fallback(rows)
        insights = generate_insights_fallback(rows)
    
    await ws.send_json({
        "type": "status",
        "data": {"message": "🎵 Recap overture incoming..."}
    })
    
    # Wait a moment for dramatic effect
    await asyncio.sleep(1.0)
    
    # Stream league table as chord progression
    for idx, item in enumerate(league[:5]):  # Top 5 domains
        pitch = 48 + idx * 4  # Spread chords across octave
        pan = 0 if idx == 0 else (-0.3 if idx % 2 else 0.3)  # Alternate pan
        vel = int(40 + item["share"] * 80)  # Volume based on share
        
        await ws.send_json({
            "type": "recap_chord",
            "data": {
                "pitch": pitch,
                "velocity": vel,
                "pan": pan,
                "duration": 2.0,
                "frequency": 261.63 * (2 ** ((pitch - 60) / 12)),  # C4 reference
                "waveform": "sine",
                "amplitude": vel / 127
            },
            "meta": {
                "domain": item["domain"],
                "share": item["share"],
                "percentage": item["percentage"],
                "rank": idx + 1
            }
        })
        
        await asyncio.sleep(0.8)  # Chord timing
    
    # Send insights for display
    await ws.send_json({
        "type": "recap_insights",
        "data": {
            "insights": insights,
            "league": league[:10],  # Top 10 for scorecard
            "total_keywords": len(set(r.get("keyword", "") for r in rows)),
            "total_results": len(rows)
        }
    })
    
    # Send completion
    await ws.send_json({
        "type": "complete",
        "data": {"message": "Stream complete - Check scorecard for recap!"}
    }) 