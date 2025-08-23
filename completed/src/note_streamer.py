import asyncio
import json
import os
from .session import get_session
from .scorecard import domain_league, generate_recap_insights

# ----------  MOTIF HELPERS  ----------
def _avg_rank(rows, domain):
    hits=[r for r in rows if r["domain"].endswith(domain)]
    return sum(r["rank"] for r in hits)/len(hits) if hits else 100

def _rank_to_transpose(rank:int)->int:
    """1 => +7 st , 100 => -5 st  (linear scale)"""
    return round((100-rank)/99*12-5)

def _rankdelta_to_tempo(delta:float)->int:
    """delta +5 => 140 BPM, 0 => 120, -5 => 100"""
    return max(90,min(140,120+delta*4))

async def _emit_motif(ws, rows, domain, last_period=None):
    rank = _avg_rank(rows, domain)
    delta = sum(r["rank_delta"] for r in rows if r["domain"].endswith(domain))/len(rows or [1])
    
    # Calculate top3 and CTR deltas if we have previous period data
    top3_delta = 0
    ctr_delta = 0
    
    if last_period:
        current_top3 = sum(1 for r in rows if r.get("rank", 100) <= 3)
        last_top3 = last_period.get("top3_count", 0)
        top3_delta = current_top3 - last_top3
        
        current_ctr = sum(r.get("ctr", 0) for r in rows) / len(rows) if rows else 0
        last_ctr = last_period.get("ctr", 0)
        ctr_delta = current_ctr - last_ctr
    
    msg = {
        "type": "motif",
        "transpose": _rank_to_transpose(rank),
        "tempo": _rankdelta_to_tempo(delta),
        "ai_steal": any(r["ai_overview"] and not r["brand_hit"] for r in rows[-10:]),
        "top3_delta": top3_delta,
        "ctr_delta": ctr_delta,
        "rank": rank
    }
    await ws.send_json(msg)
# -------------------------------------

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
    
    # Choose mapping based on metric type
    if row.get("metric_type") == "gsc":
        base = gsc_to_note(row, patch_map)
    elif row.get("metric_type") == "rank":
        base = rank_to_note(row, patch_map)
    else:
        # Fallback to original mapping for legacy data
        base = base_mapping(row, patch_map)
    
    # Apply overlays and badges (existing logic)
    # Brand win - Van Halen stab for top 3 brand hits
    if row.get("brand_hit") and row["rank"] <= 3:
        base["overlay"] = "jump_bass.mid"
        base["badge"] = "🏆"
        base["amp_mod"] = base.get("amp_mod", 1.0) * 1.5  # Boost volume
        base["duration"] = base.get("duration", 0.5) * 1.3  # Longer duration
    
    # Rank drop - lower pitch and volume for poor rankings
    if row.get("rank_delta", 0) <= int(os.getenv("INSIGHT_RANK_DROP", "-3")):
        base["transpose"] = -3
        base["velocity"] = int(base.get("velocity", 80) * 0.6)
        base["badge"] = "↓"
        base["amp_mod"] = base.get("amp_mod", 1.0) * 0.7  # Reduce volume
    
    # AI overview - special patch and panning
    if row.get("ai_overview") and not row.get("brand_hit"):
        base["patch"] = 14  # Special AI patch
        base["pan"] = 0.8   # Pan right
        base["badge"] = "🤖"
        base["waveform"] = "triangle"  # Distinctive waveform for AI
    
    # Shopping pack - snare overlay
    if row.get("rich_snippet_type") == "shopping_pack":
        base["overlay"] = "snare.wav"
        base["badge"] = "🛒"
        base["amp_mod"] = base.get("amp_mod", 1.0) * 1.2  # Slightly louder
    
    # Video results - cymbal overlay
    if row.get("rich_snippet_type") == "video":
        base["overlay"] = "video_cymbal.wav"
        base["badge"] = "🎥"
        base["amp_mod"] = base.get("amp_mod", 1.0) * 1.1
    
    # Ads slots - cash register overlay
    if row.get("ads_slot") in ("top", "shopping"):
        base["overlay"] = "cash_register.wav"
        base["badge"] = "💰"
        base["amp_mod"] = base.get("amp_mod", 1.0) * 1.15
    
    return base

def gsc_to_note(row, patch_map):
    """Map GSC data (clicks/impressions focused) to musical note."""
    # Get domain-specific patch or default
    domain = row.get('domain', '').lower()
    patch = None
    for key in patch_map:
        if key in domain:
            patch = patch_map[key]
            break
    if not patch:
        patch = patch_map.get('default', {"waveform": "sine", "amp_mod": 1.0})
    
    # Map rank to pitch (higher rank = lower pitch)
    rank = int(row.get('rank', 100))
    pitch = 60 - rank  # MIDI note number
    frequency = 440 * (2 ** ((pitch - 69) / 12))  # A4 = 440Hz, MIDI 69
    
    # Volume based on clicks (more clicks = louder)
    clicks = int(row.get('clicks', 0))
    velocity = min(100, 30 + clicks // 5)
    amplitude = velocity / 127.0 * patch.get('amp_mod', 1.0)
    
    # Duration based on impressions (more impressions = longer)
    impressions = int(row.get('impressions', 0))
    duration = 0.3 + min(0.7, impressions / 5000)
    
    return {
        "frequency": frequency,
        "pitch": pitch,
        "duration": duration,
        "amplitude": amplitude,
        "velocity": velocity,
        "waveform": patch["waveform"],
        "keyword": row.get('keyword', ''),
        "domain": row.get('domain', ''),
        "rank": rank,
        "clicks": clicks,
        "impressions": impressions,
        "metric_type": "gsc",
        "brand_hit": row.get('brand_hit', False),
        "amp_mod": patch.get('amp_mod', 1.0),
        "transpose": 0,
        "pan": 0.5
    }

def rank_to_note(row, patch_map):
    """Map rank tracker data (volume focused) to musical note."""
    # Get domain-specific patch or default
    domain = row.get('domain', '').lower()
    patch = None
    for key in patch_map:
        if key in domain:
            patch = patch_map[key]
            break
    if not patch:
        patch = patch_map.get('default', {"waveform": "sine", "amp_mod": 1.0})
    
    # Map rank to pitch (higher rank = lower pitch)
    rank = int(row.get('rank', 100))
    pitch = 60 - rank  # MIDI note number
    frequency = 440 * (2 ** ((pitch - 69) / 12))  # A4 = 440Hz, MIDI 69
    
    # Volume based on search volume (higher volume = louder)
    search_volume = int(row.get('search_volume', 0))
    velocity = min(100, 40 + search_volume // 1000)
    amplitude = velocity / 127.0 * patch.get('amp_mod', 1.0)
    
    # Standard duration for rank files
    duration = 0.5
    
    return {
        "frequency": frequency,
        "pitch": pitch,
        "duration": duration,
        "amplitude": amplitude,
        "velocity": velocity,
        "waveform": patch["waveform"],
        "keyword": row.get('keyword', ''),
        "domain": row.get('domain', ''),
        "rank": rank,
        "search_volume": search_volume,
        "metric_type": "rank",
        "brand_hit": row.get('brand_hit', False),
        "amp_mod": patch.get('amp_mod', 1.0),
        "transpose": 0,
        "pan": 0.5
    }

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

async def stream_session(ws, session_id: str, skin: str):
    """Stream notes for a session with specified skin and brand insights."""
    rows = get_session(session_id)
    if not rows:
        await ws.close(code=4404)
        return
    
    # Get skin configuration
    patch_map = SKINS.get(skin, SKINS["arena_rock"])["patch_map"]
    
    # Get client domain for motif
    client = os.getenv("CLIENT_DOMAIN", "").lower()
    streamed = []
    
    # Send status
    await ws.send_json({
        "type": "status",
        "data": {
            "message": f"Streaming {len(rows)} notes with {skin} skin",
            "total_notes": len(rows),
            "skin": skin
        }
    })
    
    # Stream notes with brand insights and motif updates
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
            streamed.append(row)
            
            # Emit motif every 8 notes (~2 bars)
            if len(streamed) % 8 == 0:
                await _emit_motif(ws, streamed, client)
            
            bars += 1
            await asyncio.sleep(0.25)  # 250ms between notes
            
        except Exception as e:
            print(f"Error streaming note {i}: {e}")
            continue
    
    # --- Recap Overture ---
    league = domain_league(rows)
    insights = generate_recap_insights(rows)
    
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

async def stream_periods(ws, session_id: str, skin: str):
    """Stream time-series periods as Van Halen-flavored musical story."""
    import logging
    logger = logging.getLogger("stream")
    logger.info(f"🎵 Starting time series streaming for session {session_id}")
    
    session_data = get_session(session_id)
    if not session_data or session_data.get("type") != "timeseries":
        logger.error(f"Invalid session data for time series: {session_data}")
        await ws.close(code=4404)
        return
    
    periods = session_data.get("periods", [])
    if not periods:
        logger.error(f"No periods found in session data")
        await ws.close(code=4404)
        return
    
    logger.info(f"🎼 Found {len(periods)} periods to stream")
    
    # Get skin configuration
    patch_map = SKINS.get(skin, SKINS["arena_rock"])["patch_map"]
    
    # Send status
    await ws.send_json({
        "type": "status",
        "data": {
            "message": f"Time series playback: {len(periods)} periods",
            "total_periods": len(periods),
            "skin": skin,
            "mode": "timeseries"
        }
    })
    
    # Progress tracking
    await ws.send_json({
        "type": "progress_init",
        "data": {"total_periods": len(periods)}
    })
    
    baseline = periods[0]
    last = baseline
    
    for idx, p in enumerate(periods, 1):
        try:
            logger.info("▶️  Streaming %s tempo=%s trans=%s",
                       p["label"], _rankdelta_to_tempo(p.get("delta_clicks", 0) / 50), _rank_to_transpose(p["avg_rank"]))
            
            # Calculate musical parameters from period metrics
            tempo = _rankdelta_to_tempo(p.get("delta_clicks", 0) / 50)
            transpose = _rank_to_transpose(p["avg_rank"])
            
            # Calculate deltas from previous period
            ctr_delta = p["ctr"] - last["ctr"] if last else 0
            top3_delta = p["top3_count"] - last["top3_count"] if last else 0
            
            logger.info(f"🎸 Period {p['label']}: tempo={tempo}, transpose={transpose}, clicks={p['click_total']}, top3={p['top3_count']}, deltas(ctr={ctr_delta:.4f}, top3={top3_delta})")
            
            # Send period start event
            await ws.send_json({
                "type": "period_start",
                "data": {
                    "period_index": idx,
                    "period_label": p["label"],
                    "tempo": tempo,
                    "transpose": transpose,
                    "metrics": {
                        "avg_rank": p["avg_rank"],
                        "top3_count": p["top3_count"],
                        "click_total": p["click_total"],
                        "ctr": p["ctr"],
                        "deltas": {
                            "clicks": p.get("delta_clicks", 0),
                            "top3": top3_delta,
                            "rank": p.get("delta_rank", 0),
                            "ctr": ctr_delta
                        }
                    }
                }
            })
            
            # Send progress update
            await ws.send_json({
                "type": "progress_update",
                "data": {"current_period": idx}
            })
            
            # Enhanced motif message with full riff parameters and deltas
            logger.info(f"Sending enhanced motif for period {p['label']}: tempo={tempo}, transpose={transpose}, top3_delta={top3_delta}, ctr_delta={ctr_delta}")
            await ws.send_json({
                "type": "motif",
                "tempo": tempo,
                "transpose": transpose,
                "top3_delta": top3_delta,
                "ctr_delta": ctr_delta,
                "period": p["label"],
                "bar": 1,
                "waveform": "sawtooth",  # Van Halen rock sound
                "amp_mod": 1.2,
                "duration": 2.0  # 2 seconds per bar
            })
            
            # Wait for bar 1 to complete
            await asyncio.sleep(2.0)
            
            # Bar 2 - Same motif with overlays for improvements
            await ws.send_json({
                "type": "motif",
                "tempo": tempo,
                "transpose": transpose,
                "period": p["label"],
                "bar": 2,
                "waveform": "sawtooth",
                "amp_mod": 1.2,
                "duration": 2.0
            })
            
            # Add overlays for newly gained top-3 keywords
            delta_top3 = p.get("delta_top3", 0)
            if delta_top3 > 0:
                for stab_count in range(min(delta_top3, 5)):  # Max 5 stabs to avoid chaos
                    await asyncio.sleep(0.3)  # Stagger the stabs
                    await ws.send_json({
                        "type": "overlay",
                        "sample": "jump_bass.wav",
                        "velocity": 100,
                        "pan": 0.0,
                        "amplitude": 0.8,
                        "badge": "🏆",
                        "reason": f"New top-3 keyword #{stab_count + 1}"
                    })
            
            # Add other overlays based on deltas
            if p.get("delta_clicks", 0) > 100:  # Significant click increase
                await ws.send_json({
                    "type": "overlay",
                    "sample": "cash.wav",
                    "velocity": 90,
                    "badge": "💰",
                    "reason": f"+{p['delta_clicks']} clicks"
                })
            
            if p.get("delta_rank", 0) < -5:  # Significant rank improvement
                await ws.send_json({
                    "type": "overlay",
                    "sample": "ai_bell.wav",
                    "velocity": 85,
                    "badge": "🚀", 
                    "reason": f"Rank improved by {abs(p['delta_rank'])} positions"
                })
            
            # Wait for bar 2 to complete
            await asyncio.sleep(1.7)  # Slightly less to account for overlay timing
            
            # Update last period for next delta calculation
            last = p
            
        except Exception as e:
            print(f"Error streaming period {idx}: {e}")
            continue
    
    # Send completion with summary
    total_click_change = periods[-1]["click_total"] - periods[0]["click_total"] if len(periods) > 1 else 0
    total_rank_change = periods[-1]["avg_rank"] - periods[0]["avg_rank"] if len(periods) > 1 else 0
    total_top3_change = periods[-1]["top3_count"] - periods[0]["top3_count"] if len(periods) > 1 else 0
    
    await ws.send_json({
        "type": "timeseries_complete",
        "data": {
            "message": "Time series playback complete!",
            "summary": {
                "periods_played": len(periods),
                "total_click_change": total_click_change,
                "total_rank_change": round(total_rank_change, 2),
                "total_top3_change": total_top3_change,
                "baseline_period": periods[0]["label"],
                "final_period": periods[-1]["label"]
            }
        }
    }) 