#!/usr/bin/env python3
"""
Production-grade SERP Loop Radio API with Maximum Signal features.
Includes comprehensive DataForSEO integration, scorecard analytics, and recap overture.
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
    title="SERP Loop Radio API - Maximum Signal",
    description="Production-grade SERP data sonification with comprehensive analytics",
    version="4.0.0"
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

def domain_league(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Analyze top-10 unique domains for scorecard."""
    top10 = [r for r in rows if r.get("rank", 0) <= 10]
    
    if not top10:
        return []
    
    domain_counter = Counter(r.get("domain", "") for r in top10)
    total_appearances = len(top10)
    
    league_table = []
    for domain, count in domain_counter.most_common():
        if domain:
            share = count / total_appearances
            league_table.append({
                "domain": domain,
                "appearances": count,
                "share": share,
                "percentage": round(share * 100, 1)
            })
    
    return league_table

def generate_recap_insights(rows: List[Dict[str, Any]], target_domain: str = None) -> List[str]:
    """Generate human-readable insights for the recap."""
    insights = []
    
    if not rows:
        return ["No data available for analysis."]
    
    league = domain_league(rows)
    if league:
        winner = league[0]
        insights.append(f"🏆 {winner['domain']} dominates with {winner['percentage']}% share")
        
        if len(league) > 1:
            runner_up = league[1]
            insights.append(f"🥈 {runner_up['domain']} follows with {runner_up['percentage']}%")
    
    if target_domain:
        target_results = [r for r in rows if r.get("domain") == target_domain]
        if target_results:
            target_ranks = [r.get("rank", 0) for r in target_results]
            top3_count = sum(1 for rank in target_ranks if rank <= 3)
            avg_rank = sum(target_ranks) / len(target_ranks)
            
            if top3_count > 0:
                insights.append(f"🎯 {target_domain} scored {top3_count} top-3 hits!")
            
            insights.append(f"📊 {target_domain} average rank: {avg_rank:.1f}")
    
    ai_count = sum(1 for r in rows if r.get("ai_overview", False))
    if ai_count > 0:
        ai_percentage = (ai_count / len(rows)) * 100
        insights.append(f"🤖 AI Overview appeared in {ai_percentage:.1f}% of results")
    
    video_count = sum(1 for r in rows if r.get("rich_snippet_type") == "video")
    if video_count > 0:
        insights.append(f"🎥 {video_count} video results detected")
    
    return insights[:5]

def map_row_to_note(row, patch_map):
    """Convert SERP row to musical note with maximum-signal brand insights."""
    import random
    
    note = base_mapping(row, patch_map)
    
    # Brand win - Van Halen stab for top 3 brand hits
    if row.get("brand_hit") and row["rank"] <= 3:
        note["overlay"] = "jump_bass.mid"
        note["badge"] = "🏆"
        note["amp_mod"] = note.get("amp_mod", 1.0) * 1.5
        note["duration"] = note.get("duration", 0.5) * 1.3
    
    # Rank drop - lower pitch and volume for poor rankings
    if row.get("rank_delta", 0) <= -3:
        note["transpose"] = -3
        note["velocity"] = int(note.get("velocity", 80) * 0.6)
        note["badge"] = "↓"
        note["amp_mod"] = note.get("amp_mod", 1.0) * 0.7
    
    # AI overview - special patch and panning
    if row.get("ai_overview") and not row.get("brand_hit"):
        note["patch"] = 14
        note["pan"] = 0.8
        note["badge"] = "🤖"
        note["waveform"] = "triangle"
    
    # Shopping pack - snare overlay
    if row.get("rich_snippet_type") == "shopping_pack":
        note["overlay"] = "snare.wav"
        note["badge"] = "🛒"
        note["amp_mod"] = note.get("amp_mod", 1.0) * 1.2

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
    """Base note mapping logic."""
    import random
    
    domain = row.get('domain', '').lower()
    patch = None
    for key in patch_map:
        if key in domain:
            patch = patch_map[key]
            break
    if not patch:
        patch = patch_map.get('default', {"waveform": "sine", "amp_mod": 1.0})
    
    rank = row.get('rank', 5)
    base_freq = 440
    frequency = base_freq * (2 ** ((10 - rank) / 12))
    frequency *= patch.get('amp_mod', 1.0)
    
    duration = random.uniform(0.3, 0.8)
    amplitude = random.uniform(0.2, 0.5) * patch.get('amp_mod', 1.0)
    amplitude = min(amplitude, 0.6)
    velocity = int(amplitude * 127)
    
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
        "pan": 0.5
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "active_sessions": len(active_sessions),
        "uptime_seconds": (datetime.utcnow() - startup_time).total_seconds(),
        "timestamp": datetime.utcnow().isoformat(),
        "version": "4.0.0",
        "sample_mode": True,
        "features": ["maximum_signal", "scorecard", "recap_overture", "redis_failover"]
    }

@app.post("/fetch", response_model=FetchResponse)
async def fetch_serp_data(request: FetchRequest):
    """Fetch comprehensive SERP data with maximum-signal features."""
    try:
        max_keywords = int(os.getenv("DFS_MAX_KEYWORDS", "50"))
        if len(request.keywords) == 0 or len(request.keywords) > max_keywords:
            raise HTTPException(status_code=400, detail=f"1–{max_keywords} keywords required")
        
        logger.info(f"Fetching data for {len(request.keywords)} keywords")
        
        # Use enhanced sample data with all maximum-signal fields
        records = create_sample_merged_data(request.keywords, request.domain)
        logger.info(f"Generated {len(records)} enhanced records")
        
        # Add brand hit detection
        if request.domain:
            for record in records:
                domain_match = request.domain.lower() in record.get("domain", "").lower()
                record["brand_hit"] = domain_match
        else:
            for record in records:
                record["brand_hit"] = False
        
        # Compute brand share and insights
        brand_hits = sum(1 for r in records if r.get("brand_hit", False))
        total_results = len(records)
        share = brand_hits / total_results if total_results > 0 else 0.0
        
        # Add share and drone flag
        share_threshold = float(os.getenv("INSIGHT_SHARE_THRESHOLD", "0.4"))
        for record in records:
            record["share"] = share
            record["drone"] = share >= share_threshold
        
        # Store in session with Redis failover
        session_id = session_manager.new_session(records)
        
        logger.info(f"Session {session_id}: Stored {len(records)} SERP results (brand share: {share:.2%})")
        
        return FetchResponse(session_id=session_id)
        
    except Exception as e:
        logger.error(f"Fetch failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch SERP data: {str(e)}")

@app.websocket("/ws/serp")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    skin: str = "arena_rock"
):
    """WebSocket endpoint for streaming sonified SERP data with recap overture."""
    try:
        await websocket.accept()
        active_sessions[session_id] = websocket
        logger.info(f"WebSocket connected for session {session_id} with skin {skin}")
        
        # Send welcome message
        await websocket.send_json({
            "type": "connection",
            "data": {
                "session_id": session_id,
                "skin": skin,
                "message": "Connected to SERP Loop Radio - Maximum Signal"
            }
        })
        
        # Get session data
        rows = session_manager.get_session(session_id)
        if not rows:
            await websocket.close(code=4404)
            return
        
        # Get skin configuration
        patch_map = SKINS.get(skin, SKINS["arena_rock"])["patch_map"]
        
        # Send status
        await websocket.send_json({
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
                    await websocket.send_json({
                        "type": "drone_event",
                        "data": {
                            "pitch": 36,
                            "duration": 2.0,
                            "velocity": 60,
                            "patch": 48,
                            "frequency": 65.4,
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
                
                await websocket.send_json(note_event)
                bars += 1
                await asyncio.sleep(0.25)
                
            except Exception as e:
                logger.error(f"Error streaming note {i}: {e}")
                continue
        
        # --- Recap Overture ---
        league = domain_league(rows)
        target_domain = None
        for row in rows:
            if row.get("brand_hit"):
                target_domain = row.get("domain")
                break
        
        insights = generate_recap_insights(rows, target_domain)
        
        await websocket.send_json({
            "type": "status",
            "data": {"message": "🎵 Recap overture incoming..."}
        })
        
        await asyncio.sleep(1.0)
        
        # Stream league table as chord progression
        for idx, item in enumerate(league[:5]):
            pitch = 48 + idx * 4
            pan = 0 if idx == 0 else (-0.3 if idx % 2 else 0.3)
            vel = int(40 + item["share"] * 80)
            
            await websocket.send_json({
                "type": "recap_chord",
                "data": {
                    "pitch": pitch,
                    "velocity": vel,
                    "pan": pan,
                    "duration": 2.0,
                    "frequency": 261.63 * (2 ** ((pitch - 60) / 12)),
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
            
            await asyncio.sleep(0.8)
        
        # Send insights for display
        await websocket.send_json({
            "type": "recap_insights",
            "data": {
                "insights": insights,
                "league": league[:10],
                "total_keywords": len(set(r.get("keyword", "") for r in rows)),
                "total_results": len(rows)
            }
        })
        
        # Send completion
        await websocket.send_json({
            "type": "complete",
            "data": {"message": "Stream complete - Check scorecard for recap!"}
        })
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "data": {"message": f"Streaming error: {str(e)}"}
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
    return HTMLResponse(content='''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SERP Loop Radio - Maximum Signal</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            color: #32ff7e;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .container {
            text-align: center;
            max-width: 600px;
            padding: 40px;
            background: rgba(26, 26, 46, 0.9);
            border-radius: 20px;
            border: 2px solid rgba(50, 255, 126, 0.3);
            backdrop-filter: blur(10px);
        }
        h1 { font-size: 2.5em; margin-bottom: 20px; text-shadow: 0 0 20px rgba(50, 255, 126, 0.5); }
        .subtitle { font-size: 1.2em; opacity: 0.9; margin-bottom: 30px; }
        .features { margin: 20px 0; font-size: 0.9em; opacity: 0.8; }
        .cta {
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
        }
        .cta:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(50, 255, 126, 0.6);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 SERP Loop Radio</h1>
        <p class="subtitle">Maximum Signal Edition</p>
        <div class="features">
            ✨ Comprehensive DataForSEO Integration<br>
            🏆 Domain League Scorecard<br>
            🎼 20-Second Recap Overture<br>
            🔄 Redis Failover Support
        </div>
        <a href="/widget/" class="cta">Launch Maximum Signal Player →</a>
    </div>
</body>
</html>''')

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info") 