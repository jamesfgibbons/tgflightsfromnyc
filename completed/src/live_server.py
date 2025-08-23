"""
FastAPI WebSocket server for SERP Loop Radio live streaming.
Handles real-time audio event streaming with Redis pub/sub integration.
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Set, Optional
import uuid

import redis.asyncio as redis
import msgpack
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

from .models import (
    NoteEvent, WebSocketMessage, LiveSession, StationConfig, 
    AudioStats, ErrorEvent, get_station_config, DEFAULT_STATIONS
)
from .mappings import MusicMappings, load_mappings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="SERP Loop Radio Live API",
    description="Real-time SERP audio streaming WebSocket API",
    version="2.0.0"
)

# CORS configuration - strict production origins
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

# Use stricter CORS in production
if os.getenv("NODE_ENV") == "production":
    # Production: Only allow HTTPS origins
    cors_origins = [origin.strip() for origin in CORS_ORIGINS if origin.strip().startswith("https://")]
    logger.info(f"Production CORS origins: {cors_origins}")
else:
    # Development: Allow localhost
    cors_origins = [origin.strip() for origin in ALLOWED_ORIGINS]
    logger.info(f"Development CORS origins: {cors_origins}")

# CORS middleware with environment-driven origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Restrict to needed methods
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Global state
redis_client: Optional[redis.Redis] = None
active_connections: Dict[str, WebSocket] = {}
active_sessions: Dict[str, LiveSession] = {}
audio_mappings: MusicMappings = load_mappings()
startup_time: datetime = datetime.utcnow()

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
LIVE_MODE_TOKEN = os.getenv("LIVE_MODE_TOKEN", "dev-token-123")
REDIS_CHANNEL = "serp_events"


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.sessions: Dict[str, LiveSession] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str, api_key: str, station: str = "daily"):
        """Accept new WebSocket connection and create session."""
        await websocket.accept()
        
        # Create session
        session = LiveSession(
            session_id=session_id,
            api_key=api_key,
            station=station
        )
        
        self.active_connections[session_id] = websocket
        self.sessions[session_id] = session
        
        logger.info(f"WebSocket connected: {session_id} on station {station}")
        
        # Send welcome message
        await self.send_personal_message(session_id, {
            "type": "connection",
            "data": {
                "session_id": session_id,
                "station": station,
                "message": "Connected to SERP Loop Radio Live"
            }
        })
    
    def disconnect(self, session_id: str):
        """Remove connection and session."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.sessions:
            del self.sessions[session_id]
        logger.info(f"WebSocket disconnected: {session_id}")
    
    async def send_personal_message(self, session_id: str, message: dict):
        """Send message to specific connection."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            try:
                # Send as binary msgpack for efficiency
                packed_data = msgpack.packb(message)
                await websocket.send_bytes(packed_data)
                
                # Update session stats
                if session_id in self.sessions:
                    self.sessions[session_id].events_sent += 1
                    self.sessions[session_id].last_activity = datetime.utcnow()
                    
            except Exception as e:
                logger.error(f"Error sending message to {session_id}: {e}")
                self.disconnect(session_id)
    
    async def broadcast_to_station(self, station: str, message: dict):
        """Broadcast message to all connections on a specific station."""
        disconnected = []
        sent_count = 0
        
        for session_id, session in self.sessions.items():
            if session.station == station and not session.muted:
                try:
                    await self.send_personal_message(session_id, message)
                    sent_count += 1
                except:
                    disconnected.append(session_id)
        
        # Clean up disconnected sessions
        for session_id in disconnected:
            self.disconnect(session_id)
        
        if sent_count > 0:
            logger.debug(f"Broadcasted to {sent_count} clients on station '{station}'")
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast message to all active connections."""
        for station in ["daily", "ai-lens", "opportunity"]:
            await self.broadcast_to_station(station, message)
    
    def get_stats(self) -> AudioStats:
        """Get current audio/connection statistics."""
        total_events = sum(session.events_sent for session in self.sessions.values())
        active_notes = len([s for s in self.sessions.values() if not s.muted])
        
        return AudioStats(
            active_notes=active_notes,
            total_events=total_events,
            session_duration=len(self.sessions),
            timestamp=datetime.utcnow()
        )


# Initialize connection manager
manager = ConnectionManager()


async def verify_api_key(api_key: str = Query(..., description="API key for authentication")):
    """Verify API key for WebSocket authentication."""
    if api_key != LIVE_MODE_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return api_key


@app.on_event("startup")
async def startup_event():
    """Initialize Redis connection on startup."""
    global redis_client
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=False)
        await redis_client.ping()
        logger.info(f"Connected to Redis at {REDIS_URL}")
        
        # Start Redis subscriber task
        asyncio.create_task(redis_subscriber())
        
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")


@app.on_event("shutdown") 
async def shutdown_event():
    """Close Redis connection on shutdown."""
    if redis_client:
        await redis_client.close()


async def redis_subscriber():
    """Subscribe to Redis channel and broadcast events to WebSocket clients."""
    if not redis_client:
        logger.error("Redis client not available")
        return
    
    try:
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(REDIS_CHANNEL)
        logger.info(f"Subscribed to Redis channel: {REDIS_CHANNEL}")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    # Deserialize event data with msgpack
                    event_data = msgpack.unpackb(message["data"])
                    
                    # Broadcast to stations based on event's station tags
                    await broadcast_to_stations(event_data)
                        
                except Exception as e:
                    logger.error(f"Error processing Redis message: {e}")
                    
    except Exception as e:
        logger.error(f"Redis subscriber error: {e}")


async def broadcast_to_stations(event_data: dict):
    """Broadcast event to appropriate stations based on event stations tag."""
    event_stations = event_data.get("stations", ["daily"])
    
    ws_message = {
        "type": "note_event",
        "data": event_data,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Broadcast to each target station
    for station in event_stations:
        await manager.broadcast_to_station(station, ws_message)





@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    try:
        # Test Redis connection
        if redis_client:
            await redis_client.ping()
            redis_status = "connected"
        else:
            redis_status = "disconnected"
        
        # Overall health status
        is_healthy = redis_status == "connected"
        
        return {
            "status": "ok" if is_healthy else "degraded",
            "redis": redis_status,
            "active_connections": len(manager.active_connections),
            "active_sessions": len(manager.sessions),
            "uptime_seconds": (datetime.utcnow() - startup_time).total_seconds(),
            "timestamp": datetime.utcnow().isoformat(),
            "version": "2.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@app.get("/stations")
async def get_stations():
    """Get available audio stations."""
    return {"stations": [station.dict() for station in DEFAULT_STATIONS]}


@app.get("/stats")
async def get_stats():
    """Get real-time statistics."""
    return manager.get_stats()


@app.websocket("/ws/serp")
async def websocket_endpoint(
    websocket: WebSocket,
    api_key: str = Query(...),
    station: str = Query(default="daily")
):
    """Main WebSocket endpoint for real-time SERP audio streaming."""
    
    # Check origin for security (prevent unauthorized WebSocket connections)
    origin = websocket.headers.get("origin")
    if origin:
        # Use the same CORS origins as HTTP endpoints
        if origin not in cors_origins:
            logger.warning(f"WebSocket connection rejected from unauthorized origin: {origin}")
            await websocket.close(code=4403, reason="Forbidden origin")
            return
        logger.info(f"WebSocket connection accepted from authorized origin: {origin}")
    else:
        # No origin header (direct connection tools like wscat)
        if os.getenv("NODE_ENV") == "production":
            logger.warning("WebSocket connection rejected: no origin header in production")
            await websocket.close(code=4403, reason="Origin header required")
            return
    
    # Verify API key
    if api_key != LIVE_MODE_TOKEN:
        await websocket.close(code=1008, reason="Invalid API key")
        return
    
    # Validate station
    if station not in ["daily", "ai-lens", "opportunity"]:
        await websocket.close(code=1003, reason="Invalid station")
        return
    
    session_id = str(uuid.uuid4())
    
    try:
        await manager.connect(websocket, session_id, api_key, station)
        
        # Send initial station config
        station_config = get_station_config(station)
        await manager.send_personal_message(session_id, {
            "type": "station_update",
            "data": station_config.dict()
        })
        
        # Listen for client messages
        while True:
            try:
                # Receive message (support both text and binary)
                try:
                    data = await websocket.receive_bytes()
                    message = msgpack.unpackb(data)
                except:
                    # Fallback to text message
                    data = await websocket.receive_text()
                    message = json.loads(data)
                
                # Handle client messages
                await handle_client_message(session_id, message)
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling client message: {e}")
                await manager.send_personal_message(session_id, {
                    "type": "error", 
                    "data": {"message": "Error processing message"}
                })
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(session_id)


async def handle_client_message(session_id: str, message: dict):
    """Handle incoming messages from WebSocket clients."""
    msg_type = message.get("type")
    data = message.get("data", {})
    
    if session_id not in manager.sessions:
        return
    
    session = manager.sessions[session_id]
    
    if msg_type == "ping":
        # Respond to ping with pong
        await manager.send_personal_message(session_id, {
            "type": "pong",
            "data": {"timestamp": datetime.utcnow().isoformat()}
        })
        
    elif msg_type == "station_change":
        # Change station
        new_station = data.get("station")
        if new_station in ["daily", "ai-lens", "opportunity"]:
            session.station = new_station
            station_config = get_station_config(new_station)
            await manager.send_personal_message(session_id, {
                "type": "station_update",
                "data": station_config.dict()
            })
            
    elif msg_type == "mute":
        # Toggle mute
        session.muted = data.get("muted", not session.muted)
        
    elif msg_type == "volume":
        # Change volume
        volume = data.get("volume", 0.8)
        session.volume = max(0.0, min(1.0, volume))
    
    # Update session activity
    session.last_activity = datetime.utcnow()
    session.events_received += 1


@app.get("/")
async def root():
    """SERP Loop Radio frontend application."""
    return HTMLResponse(content=get_frontend_html())

@app.get("/app")
async def app():
    """Alternative route for the frontend application."""
    return HTMLResponse(content=get_frontend_html())

def get_frontend_html():
    """Returns the complete frontend HTML with embedded CSS and JavaScript."""
    return """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎵</text></svg>">
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SERP Loop Radio</title>
    <style>
      :root {
        font-family: Inter, system-ui, Avenir, Helvetica, Arial, sans-serif;
        line-height: 1.5;
        font-weight: 400;
        color-scheme: light dark;
        color: rgba(255, 255, 255, 0.87);
        background-color: #242424;
        font-synthesis: none;
        text-rendering: optimizeLegibility;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        -webkit-text-size-adjust: 100%;
      }
      a {
        font-weight: 500;
        color: #646cff;
        text-decoration: inherit;
      }
      a:hover {
        color: #535bf2;
      }
      body {
        margin: 0;
        display: flex;
        place-items: center;
        min-width: 320px;
        min-height: 100vh;
      }
      h1 {
        font-size: 3.2em;
        line-height: 1.1;
      }
      button {
        border-radius: 8px;
        border: 1px solid transparent;
        padding: 0.6em 1.2em;
        font-size: 1em;
        font-weight: 500;
        font-family: inherit;
        background-color: #1a1a1a;
        color: white;
        cursor: pointer;
        transition: border-color 0.25s;
      }
      button:hover {
        border-color: #646cff;
      }
      button:focus,
      button:focus-visible {
        outline: 4px auto -webkit-focus-ring-color;
      }
      @media (prefers-color-scheme: light) {
        :root {
          color: #213547;
          background-color: #ffffff;
        }
        a:hover {
          color: #747bff;
        }
        button {
          background-color: #f9f9f9;
          color: #213547;
        }
      }
      #root {
        max-width: 1280px;
        margin: 0 auto;
        padding: 2rem;
        text-align: center;
      }
      .container {
        max-width: 800px;
        margin: 0 auto;
        padding: 20px;
        font-family: 'Arial', sans-serif;
      }
      .header {
        text-align: center;
        margin-bottom: 40px;
      }
      .header h1 {
        color: #333;
        font-size: 2.5em;
        margin-bottom: 10px;
      }
      .header p {
        color: #666;
        font-size: 1.2em;
      }
      .controls {
        display: flex;
        justify-content: center;
        gap: 20px;
        margin-bottom: 30px;
        flex-wrap: wrap;
      }
      .control-group {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 10px;
      }
      .control-group label {
        font-weight: bold;
        color: #333;
      }
      .control-group input[type="range"] {
        width: 150px;
      }
      .control-group input[type="number"] {
        width: 80px;
        padding: 5px;
        border: 1px solid #ddd;
        border-radius: 4px;
      }
      .status {
        text-align: center;
        margin-bottom: 20px;
        padding: 15px;
        border-radius: 8px;
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
      }
      .status.connected {
        background-color: #d4edda;
        border-color: #c3e6cb;
        color: #155724;
      }
      .status.disconnected {
        background-color: #f8d7da;
        border-color: #f5c6cb;
        color: #721c24;
      }
      .status.connecting {
        background-color: #fff3cd;
        border-color: #ffeaa7;
        color: #856404;
      }
      .visualization {
        width: 100%;
        height: 200px;
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #666;
      }
      .audio-info {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
      }
      .audio-info h3 {
        margin-top: 0;
        color: #333;
      }
      .audio-info p {
        margin: 5px 0;
        color: #666;
      }
      .station-controls {
        display: flex;
        justify-content: center;
        gap: 15px;
        margin-bottom: 20px;
        flex-wrap: wrap;
      }
      .station-btn {
        padding: 10px 20px;
        border: none;
        border-radius: 5px;
        cursor: pointer;
        font-weight: bold;
        transition: all 0.3s ease;
      }
      .station-btn.primary {
        background-color: #007bff;
        color: white;
      }
      .station-btn.primary:hover {
        background-color: #0056b3;
      }
      .station-btn.secondary {
        background-color: #6c757d;
        color: white;
      }
      .station-btn.secondary:hover {
        background-color: #545b62;
      }
      .station-btn.success {
        background-color: #28a745;
        color: white;
      }
      .station-btn.success:hover {
        background-color: #1e7e34;
      }
      .station-btn.danger {
        background-color: #dc3545;
        color: white;
      }
      .station-btn.danger:hover {
        background-color: #c82333;
      }
      .station-btn:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }
      .volume-meter {
        width: 100%;
        height: 20px;
        background-color: #e9ecef;
        border-radius: 10px;
        overflow: hidden;
        margin: 10px 0;
      }
      .volume-fill {
        height: 100%;
        background: linear-gradient(90deg, #28a745, #ffc107, #dc3545);
        transition: width 0.1s ease;
        width: 0%;
      }
      .frequency-display {
        font-family: monospace;
        font-size: 1.2em;
        color: #333;
        text-align: center;
        margin: 10px 0;
      }
      .error {
        color: #dc3545;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        border-radius: 4px;
        padding: 10px;
        margin: 10px 0;
      }
      .success {
        color: #155724;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 4px;
        padding: 10px;
        margin: 10px 0;
      }
      @media (max-width: 768px) {
        .controls {
          flex-direction: column;
          align-items: center;
        }
        .control-group {
          width: 100%;
          max-width: 300px;
        }
        .station-controls {
          flex-direction: column;
          align-items: center;
        }
        .station-btn {
          width: 100%;
          max-width: 200px;
        }
      }
    </style>
  </head>
  <body>
    <div id="root">
      <div class="container">
        <div class="header">
          <h1>🎵 SERP Loop Radio</h1>
          <p>Live audio synthesis from search engine ranking data</p>
        </div>

        <div id="status" class="status disconnected">
          <strong>Status:</strong> <span id="statusText">Disconnected</span>
        </div>

        <div class="controls">
          <div class="control-group">
            <label for="volume">Volume</label>
            <input type="range" id="volume" min="0" max="1" step="0.01" value="0.5">
            <input type="number" id="volumeValue" min="0" max="1" step="0.01" value="0.5">
          </div>
          <div class="control-group">
            <label for="tempo">Tempo</label>
            <input type="range" id="tempo" min="60" max="200" step="1" value="120">
            <input type="number" id="tempoValue" min="60" max="200" step="1" value="120">
          </div>
          <div class="control-group">
            <label for="reverb">Reverb</label>
            <input type="range" id="reverb" min="0" max="1" step="0.01" value="0.3">
            <input type="number" id="reverbValue" min="0" max="1" step="0.01" value="0.3">
          </div>
        </div>

        <div class="station-controls">
          <button id="playBtn" class="station-btn primary">▶️ Play</button>
          <button id="pauseBtn" class="station-btn secondary" disabled>⏸️ Pause</button>
          <button id="stopBtn" class="station-btn danger" disabled>⏹️ Stop</button>
          <button id="connectBtn" class="station-btn success">🔗 Connect</button>
        </div>

        <div class="visualization" id="visualization">
          <div>Audio visualization will appear here</div>
        </div>

        <div class="volume-meter">
          <div class="volume-fill" id="volumeMeter"></div>
        </div>

        <div class="frequency-display" id="frequencyDisplay">
          Frequency: -- Hz
        </div>

        <div class="audio-info">
          <h3>Audio Information</h3>
          <p><strong>Current Station:</strong> <span id="currentStation">None</span></p>
          <p><strong>Audio Level:</strong> <span id="audioLevel">-- dB</span></p>
          <p><strong>Connection:</strong> <span id="connectionInfo">WebSocket disconnected</span></p>
        </div>
      </div>
    </div>

    <script type="module">
      import * as Tone from 'https://cdn.skypack.dev/tone@14.7.77';

      class SERPRadio {
        constructor() {
          this.audioContext = null;
          this.synth = null;
          this.reverb = null;
          this.volume = null;
          this.isPlaying = false;
          this.isConnected = false;
          this.ws = null;
          this.currentStation = 'daily';
          this.volumeLevel = 0.5;
          this.tempo = 120;
          this.reverbLevel = 0.3;
          this.apiKey = 'dev-token-123';
          
          this.initAudio();
          this.initControls();
          this.initWebSocket();
        }

        async initAudio() {
          try {
            await Tone.start();
            console.log('Audio context started');
            
            this.volume = new Tone.Volume(-20);
            this.reverb = new Tone.Reverb(2);
            this.synth = new Tone.PolySynth(Tone.Synth, {
              oscillator: { type: 'sine' },
              envelope: { attack: 0.1, decay: 0.2, sustain: 0.3, release: 1 }
            });

            this.synth.chain(this.reverb, this.volume, Tone.destination);
            this.volume.volume.value = Tone.gainToDb(this.volumeLevel);
            this.reverb.wet.value = this.reverbLevel;
            
            console.log('Audio system initialized');
          } catch (error) {
            console.error('Failed to initialize audio:', error);
            this.showError('Failed to initialize audio system');
          }
        }

        initControls() {
          const volumeSlider = document.getElementById('volume');
          const volumeValue = document.getElementById('volumeValue');
          
          volumeSlider.addEventListener('input', (e) => {
            this.volumeLevel = parseFloat(e.target.value);
            volumeValue.value = this.volumeLevel;
            if (this.volume) {
              this.volume.volume.value = Tone.gainToDb(this.volumeLevel);
            }
          });

          volumeValue.addEventListener('input', (e) => {
            this.volumeLevel = parseFloat(e.target.value);
            volumeSlider.value = this.volumeLevel;
            if (this.volume) {
              this.volume.volume.value = Tone.gainToDb(this.volumeLevel);
            }
          });

          const tempoSlider = document.getElementById('tempo');
          const tempoValue = document.getElementById('tempoValue');
          
          tempoSlider.addEventListener('input', (e) => {
            this.tempo = parseInt(e.target.value);
            tempoValue.value = this.tempo;
            if (Tone.Transport) {
              Tone.Transport.bpm.value = this.tempo;
            }
          });

          tempoValue.addEventListener('input', (e) => {
            this.tempo = parseInt(e.target.value);
            tempoSlider.value = this.tempo;
            if (Tone.Transport) {
              Tone.Transport.bpm.value = this.tempo;
            }
          });

          const reverbSlider = document.getElementById('reverb');
          const reverbValue = document.getElementById('reverbValue');
          
          reverbSlider.addEventListener('input', (e) => {
            this.reverbLevel = parseFloat(e.target.value);
            reverbValue.value = this.reverbLevel;
            if (this.reverb) {
              this.reverb.wet.value = this.reverbLevel;
            }
          });

          reverbValue.addEventListener('input', (e) => {
            this.reverbLevel = parseFloat(e.target.value);
            reverbSlider.value = this.reverbLevel;
            if (this.reverb) {
              this.reverb.wet.value = this.reverbLevel;
            }
          });

          document.getElementById('playBtn').addEventListener('click', () => this.play());
          document.getElementById('pauseBtn').addEventListener('click', () => this.pause());
          document.getElementById('stopBtn').addEventListener('click', () => this.stop());
          document.getElementById('connectBtn').addEventListener('click', () => this.toggleConnection());
        }

        initWebSocket() {
          const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
          const wsUrl = `${protocol}//${window.location.host}/ws/serp?api_key=${this.apiKey}&station=${this.currentStation}`;
          
          this.ws = new WebSocket(wsUrl);
          
          this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.isConnected = true;
            this.updateStatus('Connected', 'connected');
            this.updateConnectionInfo('WebSocket connected');
          };
          
          this.ws.onmessage = (event) => {
            try {
              const data = JSON.parse(event.data);
              this.handleWebSocketMessage(data);
            } catch (error) {
              console.error('Failed to parse WebSocket message:', error);
            }
          };
          
          this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.isConnected = false;
            this.updateStatus('Disconnected', 'disconnected');
            this.updateConnectionInfo('WebSocket disconnected');
          };
          
          this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateStatus('Error', 'disconnected');
            this.updateConnectionInfo('WebSocket error');
          };
        }

        handleWebSocketMessage(data) {
          console.log('Received WebSocket message:', data);
          
          if (data.type === 'note_event') {
            this.handleNoteEvent(data.data);
          } else if (data.type === 'ranking_update') {
            this.handleRankingUpdate(data.data);
          } else if (data.type === 'station_change') {
            this.handleStationChange(data.data);
          }
        }

        handleNoteEvent(noteData) {
          if (this.isPlaying && this.synth) {
            const frequency = noteData.frequency || 440;
            const velocity = noteData.velocity || 0.7;
            const duration = noteData.duration || '8n';
            
            this.synth.triggerAttackRelease(frequency, duration, undefined, velocity);
            this.updateFrequencyDisplay(frequency);
          }
        }

        handleRankingUpdate(rankingData) {
          const frequency = this.mapRankingToFrequency(rankingData.position || 5);
          const velocity = this.mapRankingToVelocity(rankingData.position || 5);
          
          if (this.isPlaying && this.synth) {
            this.synth.triggerAttackRelease(frequency, '8n', undefined, velocity);
          }
          
          this.updateVisualization(rankingData);
          this.updateFrequencyDisplay(frequency);
        }

        handleStationChange(stationData) {
          this.currentStation = stationData.name;
          this.updateCurrentStation(stationData.name);
          console.log('Station changed to:', stationData.name);
        }

        mapRankingToFrequency(position) {
          const baseFreq = 220;
          const octaveRange = 2;
          const freqRatio = Math.pow(2, octaveRange / 10);
          return baseFreq * Math.pow(freqRatio, 10 - position);
        }

        mapRankingToVelocity(position) {
          return 0.1 + (position / 10) * 0.9;
        }

        play() {
          if (!this.isPlaying) {
            this.isPlaying = true;
            Tone.Transport.start();
            document.getElementById('playBtn').disabled = true;
            document.getElementById('pauseBtn').disabled = false;
            document.getElementById('stopBtn').disabled = false;
            console.log('Started playing');
          }
        }

        pause() {
          if (this.isPlaying) {
            this.isPlaying = false;
            Tone.Transport.pause();
            document.getElementById('playBtn').disabled = false;
            document.getElementById('pauseBtn').disabled = true;
            console.log('Paused');
          }
        }

        stop() {
          this.isPlaying = false;
          Tone.Transport.stop();
          if (this.synth) {
            this.synth.releaseAll();
          }
          document.getElementById('playBtn').disabled = false;
          document.getElementById('pauseBtn').disabled = true;
          document.getElementById('stopBtn').disabled = true;
          console.log('Stopped');
        }

        toggleConnection() {
          if (this.isConnected) {
            this.ws.close();
          } else {
            this.initWebSocket();
          }
        }

        updateStatus(text, className) {
          const statusElement = document.getElementById('status');
          const statusTextElement = document.getElementById('statusText');
          
          statusElement.className = `status ${className}`;
          statusTextElement.textContent = text;
        }

        updateConnectionInfo(info) {
          document.getElementById('connectionInfo').textContent = info;
        }

        updateCurrentStation(station) {
          document.getElementById('currentStation').textContent = station;
        }

        updateVisualization(data) {
          const viz = document.getElementById('visualization');
          const position = data.position || 5;
          const change = data.change || 0;
          
          const hue = (position / 10) * 360;
          const saturation = 70;
          const lightness = 50 + (change * 10);
          
          viz.style.background = `hsl(${hue}, ${saturation}%, ${lightness}%)`;
          viz.innerHTML = `
            <div style="text-align: center; color: white; text-shadow: 1px 1px 2px rgba(0,0,0,0.7);">
              <div style="font-size: 2em; font-weight: bold;">#${position}</div>
              <div style="font-size: 1.2em;">${data.keyword || 'Keyword'}</div>
              <div style="font-size: 1em;">${change > 0 ? '+' : ''}${change}</div>
            </div>
          `;
        }

        updateFrequencyDisplay(frequency) {
          document.getElementById('frequencyDisplay').textContent = 
            `Frequency: ${frequency.toFixed(1)} Hz`;
        }

        showError(message) {
          const errorDiv = document.createElement('div');
          errorDiv.className = 'error';
          errorDiv.textContent = message;
          document.querySelector('.container').appendChild(errorDiv);
          
          setTimeout(() => {
            errorDiv.remove();
          }, 5000);
        }
      }

      document.addEventListener('DOMContentLoaded', () => {
        new SERPRadio();
      });
    </script>
  </body>
</html>"""


if __name__ == "__main__":
    uvicorn.run(
        "src.live_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 