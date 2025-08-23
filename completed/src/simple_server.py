"""
Simple FastAPI server for SERP Loop Radio demo.
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Set, Optional
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="SERP Loop Radio Live API",
    description="Real-time SERP audio streaming WebSocket API",
    version="2.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for demo
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Global state
startup_time: datetime = datetime.utcnow()
active_connections: Dict[str, WebSocket] = {}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "active_connections": len(active_connections),
        "uptime_seconds": (datetime.utcnow() - startup_time).total_seconds(),
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0"
    }

@app.get("/stations")
async def get_stations():
    """Get available audio stations."""
    return {
        "stations": [
            {"id": "daily", "name": "Daily SERP", "description": "Daily SERP rankings"},
            {"id": "ai-lens", "name": "AI Lens", "description": "AI-focused keywords"},
            {"id": "opportunity", "name": "Opportunity", "description": "High-opportunity keywords"}
        ]
    }

@app.websocket("/ws/serp")
async def websocket_endpoint(
    websocket: WebSocket,
    api_key: str = Query(default="dev-token-123"),
    station: str = Query(default="daily")
):
    """WebSocket endpoint for real-time audio streaming."""
    session_id = str(uuid.uuid4())
    
    try:
        await websocket.accept()
        active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: {session_id} on station {station}")
        
        # Send welcome message
        await websocket.send_json({
            "type": "connection",
            "data": {
                "session_id": session_id,
                "station": station,
                "message": "Connected to SERP Loop Radio Live"
            }
        })
        
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Echo back ping messages
                if message.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "data": {"timestamp": datetime.utcnow().isoformat()}
                    })
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        if session_id in active_connections:
            del active_connections[session_id]
        logger.info(f"WebSocket disconnected: {session_id}")

@app.get("/")
async def root():
    """SERP Loop Radio frontend application."""
    return HTMLResponse(content=get_frontend_html())

@app.get("/app")
async def app_route():
    """Alternative route for the frontend application."""
    return HTMLResponse(content=get_frontend_html())

def get_frontend_html():
    """Returns the complete frontend HTML with embedded CSS and JavaScript."""
    return '''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎵</text></svg>">
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SERP Loop Radio</title>
    <style>
      body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
        margin: 0;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
      }
      .container {
        text-align: center;
        max-width: 800px;
        padding: 40px;
        background: rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        backdrop-filter: blur(10px);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
      }
      h1 {
        font-size: 3em;
        margin-bottom: 10px;
        background: linear-gradient(45deg, #fff, #f0f0f0);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }
      .subtitle {
        font-size: 1.2em;
        opacity: 0.9;
        margin-bottom: 30px;
      }
      .status {
        display: inline-block;
        padding: 10px 20px;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 25px;
        margin: 10px;
        font-weight: 500;
      }
      .status.connected {
        background: rgba(76, 175, 80, 0.3);
      }
      .status.disconnected {
        background: rgba(244, 67, 54, 0.3);
      }
      .controls {
        margin: 30px 0;
      }
      button {
        background: rgba(255, 255, 255, 0.2);
        border: 2px solid rgba(255, 255, 255, 0.3);
        color: white;
        padding: 12px 24px;
        border-radius: 25px;
        cursor: pointer;
        margin: 5px;
        font-size: 16px;
        transition: all 0.3s ease;
      }
      button:hover {
        background: rgba(255, 255, 255, 0.3);
        border-color: rgba(255, 255, 255, 0.5);
        transform: translateY(-2px);
      }
      button:active {
        transform: translateY(0);
      }
      .station-selector {
        margin: 20px 0;
      }
      select {
        background: rgba(255, 255, 255, 0.2);
        border: 2px solid rgba(255, 255, 255, 0.3);
        color: white;
        padding: 10px 15px;
        border-radius: 15px;
        font-size: 16px;
      }
      .visualizer {
        width: 100%;
        height: 200px;
        background: rgba(0, 0, 0, 0.2);
        border-radius: 15px;
        margin: 20px 0;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        opacity: 0.7;
      }
      .info {
        text-align: left;
        margin-top: 30px;
        padding: 20px;
        background: rgba(0, 0, 0, 0.1);
        border-radius: 15px;
        font-size: 14px;
        line-height: 1.6;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>🎵 SERP Loop Radio</h1>
      <p class="subtitle">Live SERP Data Sonification</p>
      
      <div id="status" class="status disconnected">Disconnected</div>
      
      <div class="station-selector">
        <label for="station">Station: </label>
        <select id="station">
          <option value="daily">Daily SERP</option>
          <option value="ai-lens">AI Lens</option>
          <option value="opportunity">Opportunity</option>
        </select>
      </div>
      
      <div class="controls">
        <button id="connectBtn">Connect</button>
        <button id="disconnectBtn" disabled>Disconnect</button>
        <button id="muteBtn" disabled>Mute</button>
      </div>
      
      <div class="visualizer" id="visualizer">
        Audio visualization will appear here when connected
      </div>
      
      <div class="info">
        <h3>About SERP Loop Radio</h3>
        <p>This is a live audio sonification of SERP (Search Engine Results Page) ranking data. Each ranking change is converted into musical notes using the FATLD (Frequency, Amplitude, Timbre, Location, Duration) mapping system.</p>
        <p><strong>How it works:</strong></p>
        <ul>
          <li>🔍 SERP data is collected daily from search engines</li>
          <li>🎼 Ranking changes are mapped to musical parameters</li>
          <li>🎵 Audio events are streamed live via WebSocket</li>
          <li>🎧 Your browser synthesizes the audio in real-time</li>
        </ul>
        <p><strong>Demo Mode:</strong> Currently running with sample data for demonstration purposes.</p>
      </div>
    </div>

    <script>
      let ws = null;
      let audioContext = null;
      let isConnected = false;
      let isMuted = false;
      
      const statusEl = document.getElementById('status');
      const connectBtn = document.getElementById('connectBtn');
      const disconnectBtn = document.getElementById('disconnectBtn');
      const muteBtn = document.getElementById('muteBtn');
      const stationSelect = document.getElementById('station');
      const visualizer = document.getElementById('visualizer');
      
      // Initialize audio context on user interaction
      async function initAudio() {
        if (!audioContext) {
          audioContext = new (window.AudioContext || window.webkitAudioContext)();
          if (audioContext.state === 'suspended') {
            await audioContext.resume();
          }
        }
      }
      
      function updateStatus(status, message) {
        statusEl.textContent = message;
        statusEl.className = `status ${status}`;
        isConnected = status === 'connected';
        
        connectBtn.disabled = isConnected;
        disconnectBtn.disabled = !isConnected;
        muteBtn.disabled = !isConnected;
      }
      
      function connect() {
        if (ws) return;
        
        initAudio();
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/serp?api_key=dev-token-123&station=${stationSelect.value}`;
        
        ws = new WebSocket(wsUrl);
        
        ws.onopen = function() {
          updateStatus('connected', 'Connected to SERP Loop Radio');
          visualizer.textContent = 'Connected! Waiting for audio events...';
        };
        
        ws.onmessage = function(event) {
          try {
            const message = JSON.parse(event.data);
            handleMessage(message);
          } catch (e) {
            console.error('Error parsing message:', e);
          }
        };
        
        ws.onclose = function() {
          updateStatus('disconnected', 'Disconnected');
          visualizer.textContent = 'Audio visualization will appear here when connected';
          ws = null;
        };
        
        ws.onerror = function(error) {
          console.error('WebSocket error:', error);
          updateStatus('disconnected', 'Connection error');
        };
      }
      
      function disconnect() {
        if (ws) {
          ws.close();
          ws = null;
        }
      }
      
      function toggleMute() {
        isMuted = !isMuted;
        muteBtn.textContent = isMuted ? 'Unmute' : 'Mute';
      }
      
      function handleMessage(message) {
        console.log('Received message:', message);
        
        switch (message.type) {
          case 'connection':
            visualizer.textContent = `Connected to station: ${message.data.station}`;
            break;
          case 'note_event':
            if (!isMuted) {
              playNote(message.data);
            }
            visualizer.textContent = `♪ Playing note: ${message.data.note || 'C4'} (${new Date().toLocaleTimeString()})`;
            break;
          case 'pong':
            // Handle ping/pong for keepalive
            break;
        }
      }
      
      function playNote(noteData) {
        if (!audioContext || isMuted) return;
        
        try {
          const oscillator = audioContext.createOscillator();
          const gainNode = audioContext.createGain();
          
          oscillator.connect(gainNode);
          gainNode.connect(audioContext.destination);
          
          // Map note data to audio parameters
          const frequency = noteData.frequency || 440;
          const duration = (noteData.duration || 0.5) * 1000;
          const volume = Math.min(noteData.amplitude || 0.3, 0.5);
          
          oscillator.frequency.setValueAtTime(frequency, audioContext.currentTime);
          oscillator.type = noteData.waveform || 'sine';
          
          gainNode.gain.setValueAtTime(0, audioContext.currentTime);
          gainNode.gain.linearRampToValueAtTime(volume, audioContext.currentTime + 0.01);
          gainNode.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + duration / 1000);
          
          oscillator.start(audioContext.currentTime);
          oscillator.stop(audioContext.currentTime + duration / 1000);
          
        } catch (e) {
          console.error('Error playing note:', e);
        }
      }
      
      // Event listeners
      connectBtn.addEventListener('click', connect);
      disconnectBtn.addEventListener('click', disconnect);
      muteBtn.addEventListener('click', toggleMute);
      
      stationSelect.addEventListener('change', function() {
        if (isConnected) {
          disconnect();
          setTimeout(connect, 100);
        }
      });
      
      // Send periodic ping to keep connection alive
      setInterval(function() {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({type: 'ping', data: {}}));
        }
      }, 30000);
      
      // Auto-connect on page load
      setTimeout(function() {
        if (!isConnected) {
          connect();
        }
      }, 1000);
    </script>
  </body>
</html>'''

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 