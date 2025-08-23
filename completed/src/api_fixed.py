"""
Main API for SERP Loop Radio with DataForSEO integration and Redis session management.
"""

import os
import json
import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# Fixed imports for production
import session
import note_streamer
try:
    import dfs_client
    import merge
except ImportError:
    # Fallback for production
    dfs_client = None
    merge = None

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
    title="SERP Loop Radio API",
    description="Interactive SERP data sonification with DataForSEO",
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

# Configuration
DATAFORSEO_LOGIN = os.getenv("DATAFORSEO_LOGIN")
DATAFORSEO_PASSWORD = os.getenv("DATAFORSEO_PASSWORD")
USE_SAMPLE_DATA = os.getenv("USE_SAMPLE_DATA", "true").lower() == "true"

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "active_sessions": len(active_sessions),
        "uptime_seconds": (datetime.utcnow() - startup_time).total_seconds(),
        "timestamp": datetime.utcnow().isoformat(),
        "version": "4.0.0",
        "sample_mode": USE_SAMPLE_DATA,
        "dfs_configured": bool(DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD)
    }

@app.post("/fetch", response_model=FetchResponse)
async def fetch_serp_data(request: FetchRequest):
    """Fetch comprehensive SERP data with DataForSEO integration."""
    try:
        # Validate keywords (1-50 required)
        max_keywords = int(os.getenv("DFS_MAX_KEYWORDS", "50"))
        if len(request.keywords) == 0 or len(request.keywords) > max_keywords:
            raise HTTPException(status_code=400, detail=f"1–{max_keywords} keywords required")
        
        logger.info(f"Fetching data for {len(request.keywords)} keywords")
        
        if USE_SAMPLE_DATA or not (DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD) or not dfs_client or not merge:
            # Use enhanced sample data
            records = create_sample_merged_data(request.keywords, request.domain)
            logger.info(f"Using sample data: {len(records)} records generated")
        else:
            # Use real DataForSEO API with comprehensive data
            try:
                records = await dfs_client.dfs_batch(request.keywords)
                logger.info(f"DataForSEO API returned {len(records)} records")
            except Exception as e:
                logger.error(f"DataForSEO API failed: {e}, falling back to sample data")
                records = create_sample_merged_data(request.keywords, request.domain)
        
        if not records:
            raise HTTPException(status_code=500, detail="No SERP data retrieved")
        
        # Add brand hit detection if domain specified
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
        
        # Add share and drone flag to all records
        share_threshold = float(os.getenv("INSIGHT_SHARE_THRESHOLD", "0.4"))
        for record in records:
            record["share"] = share
            record["drone"] = share >= share_threshold
        
        # Store in Redis session
        session_id = session.new_session(records)
        
        logger.info(f"Session {session_id}: Stored {len(records)} SERP results (brand share: {share:.2%})")
        
        return FetchResponse(session_id=session_id)
        
    except Exception as e:
        logger.error(f"Fetch failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch SERP data: {str(e)}")

def create_sample_merged_data(keywords: List[str], domain: str = None) -> List[Dict]:
    """Create sample merged data for testing/demo purposes."""
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
        # Generate 10 sample results per keyword
        for rank in range(1, 11):
            # Higher chance for target domain to appear in top positions
            if domain and rank <= 3 and random.random() > 0.7:
                result_domain = domain
            else:
                result_domain = random.choice(sample_domains)
            
            # Sample rich snippet types
            rich_types = ["video", "shopping_pack", "featured_snippet", "local_pack", None]
            rich_type = random.choice(rich_types) if random.random() < 0.3 else None
            
            # Sample ads positions
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

@app.websocket("/ws/serp")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    skin: str = "arena_rock"
):
    """WebSocket endpoint for streaming sonified SERP data."""
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
                "message": "Connected to SERP Loop Radio"
            }
        })
        
        # Start streaming notes
        await note_streamer.stream_session(websocket, session_id, skin)
        
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

# Serve main app
@app.get("/")
async def root():
    """Main app route."""
    return HTMLResponse(content=get_main_app_html())

@app.get("/app")
async def app_route():
    """Alternative app route."""
    return HTMLResponse(content=get_main_app_html())

def get_main_app_html():
    """Returns the main app HTML."""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SERP Loop Radio</title>
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
        <p class="subtitle">Live SERP Data Sonification</p>
        <a href="/widget/" class="cta">Launch Interactive Player →</a>
    </div>
</body>
</html>'''

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 