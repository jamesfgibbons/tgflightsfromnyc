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
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from .session import new_session, get_session, get_session_stats
from .note_streamer import stream_session, stream_periods, map_row_to_note, SKINS
from .dfs_client import dfs_batch
from .merge import create_sample_merged_data
from .csv_ingest import load_csv, validate_csv_format
from .api_time import router as ts_router

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

# Include time series router
app.include_router(ts_router)

# Global state
active_sessions: Dict[str, WebSocket] = {}
startup_time: datetime = datetime.utcnow()

# Configuration
DATAFORSEO_LOGIN = os.getenv("DATAFORSEO_LOGIN")
DATAFORSEO_PASSWORD = os.getenv("DATAFORSEO_PASSWORD")
USE_SAMPLE_DATA = os.getenv("USE_SAMPLE_DATA", "true").lower() == "true"

# Create MIDI directory and cleanup old files on startup
def cleanup_old_midi_files():
    """Remove MIDI files older than 24 hours."""
    midi_dir = "/tmp/midi"
    try:
        os.makedirs(midi_dir, exist_ok=True)
        
        if not os.path.exists(midi_dir):
            return
            
        current_time = time.time()
        day_in_seconds = 24 * 60 * 60
        cleaned_count = 0
        
        for filename in os.listdir(midi_dir):
            if filename.endswith('.mid'):
                filepath = os.path.join(midi_dir, filename)
                file_age = current_time - os.path.getmtime(filepath)
                
                if file_age > day_in_seconds:
                    os.remove(filepath)
                    cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} old MIDI files")
            
    except Exception as e:
        logger.warning(f"MIDI cleanup failed: {e}")

# Run cleanup on startup
cleanup_old_midi_files()

@app.get("/health")
async def health_check():
    """Health check endpoint with session storage monitoring."""
    session_stats = get_session_stats()
    
    return {
        "status": "ok",
        "active_sessions": len(active_sessions),
        "uptime_seconds": (datetime.utcnow() - startup_time).total_seconds(),
        "timestamp": datetime.utcnow().isoformat(),
        "version": "4.0.0",
        "sample_mode": USE_SAMPLE_DATA,
        "dfs_configured": bool(DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD),
        "session_storage": session_stats
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
        
        if USE_SAMPLE_DATA or not (DATAFORSEO_LOGIN and DATAFORSEO_PASSWORD):
            # Use enhanced sample data
            records = create_sample_merged_data(request.keywords, request.domain)
            logger.info(f"Using sample data: {len(records)} records generated")
        else:
            # Use real DataForSEO API with comprehensive data
            try:
                records = await dfs_batch(request.keywords)
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
        session_id = new_session(records)
        
        logger.info(f"Session {session_id}: Stored {len(records)} SERP results (brand share: {share:.2%})")
        
        return FetchResponse(session_id=session_id)
        
    except Exception as e:
        logger.error(f"Fetch failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch SERP data: {str(e)}")

@app.post("/upload")
async def upload_csv(declared_type: str = Form(""), file: UploadFile = File(...)):
    """Upload and process CSV files (GSC or Rank File format)."""
    try:
        logger.info(f"Uploading CSV: {file.filename}, declared type: {declared_type}")
        
        # Read file content
        content = await file.read()
        
        # Process CSV using the updated load_csv function
        rows = load_csv(content, file.filename, declared_type)
        
        if not rows:
            raise HTTPException(status_code=400, detail="No data found in CSV file")
        
        # Validate and get format info
        format_info = validate_csv_format(rows)
        
        # Store in session
        session_id = new_session(rows)
        
        logger.info(f"Session {session_id}: Processed {len(rows)} CSV rows, format: {format_info['format']}")
        
        return {
            "session_id": session_id,
            "row_count": len(rows),
            "format": format_info["format"],
            "total_rows": format_info["total_rows"],
            "status": "success"
        }
        
    except ValueError as e:
        logger.error(f"CSV validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process upload: {str(e)}")

@app.get("/download/midi")
async def download_midi(session: str, mode: str = "time"):
    """Generate and download MIDI file from session data."""
    try:
        # Get session data
        rows = get_session(session)
        if not rows:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Create MIDI export
        midi_content = generate_midi_from_session(rows, mode)
        
        # Ensure tmp/midi directory exists
        os.makedirs("/tmp/midi", exist_ok=True)
        
        # Save to temporary file
        filename = f"serpradio_{session[:8]}_{mode}.mid"
        filepath = f"/tmp/midi/{filename}"
        
        with open(filepath, "wb") as f:
            f.write(midi_content)
        
        logger.info(f"Generated MIDI export: {filename}")
        
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type="audio/midi",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"MIDI export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate MIDI: {str(e)}")

def generate_midi_from_session(rows, mode="time"):
    """Generate professional MIDI bytes from session data."""
    try:
        # Get session metadata for track naming
        client_domain = os.getenv("CLIENT_DOMAIN", "unknown")
        date_range = get_date_range_from_rows(rows)
        
        # Basic MIDI file header (format 0, 1 track, 480 ticks per quarter note)
        header = bytes([
            0x4D, 0x54, 0x68, 0x64,  # "MThd"
            0x00, 0x00, 0x00, 0x06,  # Header length
            0x00, 0x00,              # Format 0
            0x00, 0x01,              # 1 track
            0x01, 0xE0               # 480 ticks per quarter note
        ])
        
        # Track header
        track_header = bytes([
            0x4D, 0x54, 0x72, 0x6B,  # "MTrk"
        ])
        
        # Generate track data from session rows
        track_data = bytearray()
        
        # Add track name
        track_name = f"SERP-Radio-{client_domain}-{date_range}"
        track_name_bytes = track_name.encode('ascii')[:127]  # MIDI text limit
        track_data.extend([0x00, 0xFF, 0x03, len(track_name_bytes)])
        track_data.extend(track_name_bytes)
        
        # Add initial tempo (120 BPM default)
        tempo_us_per_quarter = 500000  # 120 BPM in microseconds per quarter note
        track_data.extend([0x00, 0xFF, 0x51, 0x03])
        track_data.extend(tempo_us_per_quarter.to_bytes(3, 'big'))
        
        # Get patch mapping for note generation
        patch_map = SKINS.get("arena_rock", SKINS["synth_pop"])["patch_map"]
        
        current_time = 0
        current_tempo = 120
        
        for i, row in enumerate(rows[:100]):  # Limit to first 100 notes for performance
            note_data = map_row_to_note(row, patch_map)
            
            # Convert to MIDI note with proper bounds checking
            midi_note = max(21, min(108, int(note_data.get("pitch", 60))))
            velocity = max(1, min(127, int(note_data.get("velocity", 64))))
            duration_ticks = int(note_data.get("duration", 0.5) * 480)  # Convert to ticks
            
            # Add tempo change if motif tempo has changed
            if hasattr(note_data, 'tempo') and note_data.get('tempo') != current_tempo:
                new_tempo = note_data['tempo']
                tempo_us = int(60000000 / new_tempo)  # Convert BPM to microseconds
                track_data.extend([0x00, 0xFF, 0x51, 0x03])
                track_data.extend(tempo_us.to_bytes(3, 'big'))
                current_tempo = new_tempo
            
            # Note on event (delta time 0, note on channel 0, note, velocity)
            track_data.extend([0x00, 0x90, midi_note, velocity])
            
            # Note off event (after duration)
            delta_time = duration_ticks
            if delta_time > 127:
                # Variable length quantity encoding for large delta times
                while delta_time > 127:
                    track_data.extend([0x81, delta_time & 0x7F])
                    delta_time >>= 7
            track_data.extend([delta_time, 0x80, midi_note, 0x40])
            
            # Add timing between notes (250ms = 120 ticks at 120 BPM)
            current_time += 120
        
        # End of track
        track_data.extend([0x00, 0xFF, 0x2F, 0x00])
        
        # Track length
        track_length = len(track_data).to_bytes(4, 'big')
        
        # Combine all parts
        midi_file = header + track_header + track_length + track_data
        
        logger.info(f"Generated MIDI: {len(midi_file)} bytes, {len(rows)} source rows")
        return midi_file
        
    except Exception as e:
        logger.error(f"MIDI generation failed: {e}")
        raise ValueError(f"Could not generate MIDI: {str(e)}")

def get_date_range_from_rows(rows):
    """Extract date range from CSV rows for MIDI track naming."""
    try:
        dates = [row.get("date") for row in rows if row.get("date")]
        if not dates:
            return "no-date"
        
        min_date = min(dates)
        max_date = max(dates)
        
        if min_date == max_date:
            return str(min_date).replace("-", "")
        else:
            return f"{min_date}_{max_date}".replace("-", "")
    except:
        return "unknown-date"

@app.websocket("/ws/serp")
async def ws_serp(
    ws: WebSocket,
    session_id: str,
    skin: str = "arena_rock",
    mode: str = ""
):
    """WebSocket endpoint for streaming sonified SERP data."""
    try:
        await ws.accept()
        active_sessions[session_id] = ws
        logger.info(f"WebSocket connected for session {session_id} with skin {skin}")
        
        # Get session data and route appropriately
        sess = get_session(session_id)
        if not sess:
            logger.error(f"No session found for {session_id}")
            return await ws.close(code=4404)
        
        # Send welcome message
        await ws.send_json({
            "type": "connection",
            "data": {
                "session_id": session_id,
                "skin": skin,
                "message": "Connected to SERP Loop Radio"
            }
        })
        
        # Route based on session type
        if isinstance(sess, list):  # legacy snapshot
            logger.info(f"Routing to stream_session for legacy session {session_id}")
            await stream_session(ws, session_id, skin)
        elif isinstance(sess, dict) and sess.get("type") == "timeseries":
            logger.info(f"Routing to stream_periods for time series session {session_id}")
            await stream_periods(ws, session_id, skin)
        else:
            logger.error(f"Unknown session type for {session_id}: {type(sess)}")
            await ws.close(code=4400)
        
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