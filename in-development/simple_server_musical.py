#!/usr/bin/env python3
"""
Musical SERP Loop Radio API with Van Halen "Jump" Motif
Production-grade server with real-time melody morphing based on SERP data trends.
"""

import os
import json
import asyncio
import logging
import uuid
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import Counter

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models
class FetchRequest(BaseModel):
    keywords: List[str]
    domain: Optional[str] = None

class FetchResponse(BaseModel):
    session_id: str
    status: str = "success"

# FastAPI app
app = FastAPI(
    title="SERP Loop Radio - Musical Edition",
    description="Van Halen Jump motif with real-time SERP data morphing",
    version="4.1.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Global state
active_sessions: Dict[str, WebSocket] = {}
startup_time: datetime = datetime.utcnow()

# Musical motif state
motif_state = {"bars": 0, "next_emit": 0, "transpose": 0, "tempo": 120}

# Session management with Redis failover
class SessionManager:
    def __init__(self):
        self.redis_client = None
        self.fallback_storage = {}
        
        try:
            import redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True, socket_timeout=5)
            self.redis_client.ping()
            logger.info(f"✅ Connected to Redis at {redis_url}")
        except Exception as e:
            logger.warning(f"⚠️  Redis connection failed: {e}. Using in-memory fallback.")
            self.redis_client = None

    def new_session(self, data: List[Dict[Any, Any]]) -> str:
        sid = str(uuid.uuid4())
        session_data = {
            "data": data,
            "created_at": time.time(),
            "id": sid
        }
        
        try:
            if self.redis_client:
                self.redis_client.setex(f"session:{sid}", 3600, json.dumps(session_data))
            else:
                self.fallback_storage[sid] = session_data
            return sid
        except Exception as e:
            logger.warning(f"Session storage error: {e}. Using fallback.")
            self.fallback_storage[sid] = session_data
            return sid

    def get_session(self, sid: str) -> Optional[List[Dict[Any, Any]]]:
        try:
            if self.redis_client:
                session_json = self.redis_client.get(f"session:{sid}")
                if session_json:
                    session_data = json.loads(session_json)
                    return session_data.get("data")
            
            session_data = self.fallback_storage.get(sid)
            if session_data:
                return session_data.get("data")
                
        except Exception as e:
            logger.warning(f"Session retrieval error: {e}. Checking fallback.")
            session_data = self.fallback_storage.get(sid)
            if session_data:
                return session_data.get("data")
        
        return None

# Global session manager
session_manager = SessionManager()

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

def scale(value, in_min, in_max, out_min, out_max):
    """Scale a value from one range to another."""
    return ((value - in_min) * (out_max - out_min) / (in_max - in_min)) + out_min

def clamp(value, min_val, max_val):
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))

def create_sample_merged_data(keywords: List[str], domain: str = None) -> List[Dict]:
    """Create enhanced sample SERP data with all maximum-signal fields."""
    import random
    
    sample_domains = [
        'google.com', 'youtube.com', 'amazon.com', 'wikipedia.org', 'facebook.com',
        'twitter.com', 'instagram.com', 'linkedin.com', 'reddit.com', 'tiktok.com',
        'github.com', 'stackoverflow.com', 'medium.com', 'quora.com', 'pinterest.com'
    ]
    
    if domain:
        sample_domains.insert(0, domain)
    
    records = []
    for keyword in keywords:
        for rank in range(1, 11):
            if domain and rank <= 3 and random.random() > 0.7:
                result_domain = domain
            else:
                result_domain = random.choice(sample_domains)
            
            rich_types = ["video", "shopping_pack", "featured_snippet", "local_pack", None]
            rich_type = random.choice(rich_types) if random.random() < 0.3 else None
            
            ads_positions = ["top", "bottom", "shopping", None]
            ads_slot = random.choice(ads_positions) if random.random() < 0.2 else None
            
            record = {
                "keyword": keyword,
                "rank": rank,
                "domain": result_domain,
                "url": f"https://{result_domain}/search?q={keyword.replace(' ', '+')}",
                "title": f"{keyword.title()} - {result_domain.title()}",
                "rank_delta": random.randint(-5, 3),
                "ai_overview": random.random() < 0.15 and rank <= 5,
                "rich_snippet_type": rich_type,
                "ads_slot": ads_slot,
                "search_volume": random.randint(100, 50000),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            records.append(record)
    
    return records

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
    
    logger.info(f"🎵 Motif update: transpose={transpose}, tempo={tempo}, ai_steal={ai_steal}, competitor_ahead={competitor_ahead}")
    
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

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "active_sessions": len(active_sessions),
        "uptime_seconds": (datetime.utcnow() - startup_time).total_seconds(),
        "timestamp": datetime.utcnow().isoformat(),
        "version": "4.1.0",
        "sample_mode": True,
        "features": ["van_halen_motif", "musical_morphing", "scorecard_overture", "redis_failover"],
        "client_domain": os.getenv("CLIENT_DOMAIN", "Not set")
    }

@app.post("/fetch", response_model=FetchResponse)
async def fetch_serp_data(request: FetchRequest):
    """Fetch comprehensive SERP data with musical features."""
    try:
        max_keywords = int(os.getenv("DFS_MAX_KEYWORDS", "50"))
        if len(request.keywords) == 0 or len(request.keywords) > max_keywords:
            raise HTTPException(status_code=400, detail=f"1–{max_keywords} keywords required")
        
        logger.info(f"🎵 Fetching musical data for {len(request.keywords)} keywords")
        
        # Use enhanced sample data with all maximum-signal fields
        records = create_sample_merged_data(request.keywords, request.domain)
        logger.info(f"Generated {len(records)} enhanced musical records")
        
        # Add brand hit detection
        if request.domain:
            for record in records:
                domain_match = request.domain.lower() in record.get("domain", "").lower()
                record["brand_hit"] = domain_match
        else:
            for record in records:
                record["brand_hit"] = False
        
        # Store in session with Redis failover
        session_id = session_manager.new_session(records)
        
        logger.info(f"🎵 Musical session {session_id}: Stored {len(records)} SERP results")
        
        return FetchResponse(session_id=session_id)
        
    except Exception as e:
        logger.error(f"Musical fetch failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch SERP data: {str(e)}")

@app.websocket("/ws/serp")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    skin: str = "arena_rock"
):
    """WebSocket endpoint for streaming musical SERP data with Van Halen motif."""
    try:
        await websocket.accept()
        active_sessions[session_id] = websocket
        logger.info(f"🎵 Musical WebSocket connected for session {session_id} with skin {skin}")
        
        # Send welcome message
        await websocket.send_json({
            "type": "connection",
            "data": {
                "session_id": session_id,
                "skin": skin,
                "message": "🎸 Connected to Musical SERP Loop Radio - Van Halen Edition"
            }
        })
        
        # Get session data
        rows = session_manager.get_session(session_id)
        if not rows:
            await websocket.close(code=4404)
            return
        
        client_domain = os.getenv("CLIENT_DOMAIN", "")
        streamed = []
        
        # Get skin patch map
        patch_map = SKINS.get(skin, SKINS["arena_rock"])["patch_map"]
        
        logger.info(f"🎵 Starting musical stream for {len(rows)} rows with client domain: {client_domain}")
        
        # Send initial motif setup
        await websocket.send_json({
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
            
            await websocket.send_json(note_event)
            
            # Update motif every 4 bars
            motif_state["bars"] += 1
            if motif_state["bars"] >= 4:
                motif_state["bars"] = 0
                await emit_motif(websocket, streamed, client_domain)
            
            await asyncio.sleep(0.25)
        
        # Play scorecard overture
        await emit_scorecard_overture(websocket, rows, client_domain)
        
        # Send completion
        await websocket.send_json({
            "type": "complete",
            "data": {"message": "🎵 Musical stream complete - Van Halen style!"}
        })
        
    except WebSocketDisconnect:
        logger.info(f"🎵 Musical WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"🎵 Musical WebSocket error for session {session_id}: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"message": f"Musical streaming error: {str(e)}"}
            })
        except:
            pass
    finally:
        if session_id in active_sessions:
            del active_sessions[session_id]

# Serve widget files
try:
    app.mount("/widget", StaticFiles(directory="widget", html=True), name="widget")
except Exception as e:
    logger.warning(f"Could not mount widget directory: {e}")

@app.get("/")
async def root():
    """Main app route."""
    client_domain = os.getenv("CLIENT_DOMAIN", "your-domain.com")
    return HTMLResponse(content=f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SERP Loop Radio - Van Halen Musical Edition</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            color: #32ff7e;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .container {{
            text-align: center;
            max-width: 700px;
            padding: 40px;
            background: rgba(26, 26, 46, 0.9);
            border-radius: 20px;
            border: 2px solid rgba(50, 255, 126, 0.3);
            backdrop-filter: blur(10px);
        }}
        h1 {{ font-size: 2.5em; margin-bottom: 20px; text-shadow: 0 0 20px rgba(50, 255, 126, 0.5); }}
        .subtitle {{ font-size: 1.2em; opacity: 0.9; margin-bottom: 30px; }}
        .features {{ margin: 20px 0; font-size: 0.9em; opacity: 0.8; }}
        .client-info {{ 
            background: rgba(50, 255, 126, 0.1); 
            padding: 15px; 
            border-radius: 10px; 
            margin: 20px 0; 
            border-left: 4px solid #32ff7e;
        }}
        .cta {{
            display: inline-block;
            padding: 15px 30px;
            background: linear-gradient(135deg, #32ff7e 0%, #2ed573 100%);
            color: #1a1a2e;
            text-decoration: none;
            font-size: 18px;
            font-weight: 600;
            border-radius: 25px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(50, 255, 126, 0.4);
        }}
        .cta:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(50, 255, 126, 0.6);
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎸 SERP Loop Radio</h1>
        <p class="subtitle">Van Halen Musical Edition</p>
        <div class="client-info">
            <strong>🎯 Client Domain:</strong> {client_domain}<br>
            <small>Set CLIENT_DOMAIN environment variable to customize</small>
        </div>
        <div class="features">
            🎵 Van Halen "Jump" Bass Motif<br>
            🎸 Real-time Musical Morphing<br>
            🏆 Brand Win Detection & Stabs<br>
            🤖 AI Overview Alerts<br>
            🎼 Scorecard Overture Finale<br>
            🔄 Redis Failover Support
        </div>
        <a href="/widget/" class="cta">🎸 Launch Musical Player →</a>
    </div>
</body>
</html>''')

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info") 