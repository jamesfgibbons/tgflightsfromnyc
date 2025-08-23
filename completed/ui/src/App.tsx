import { useState, useEffect, useRef, useCallback } from 'react';
import * as Tone from 'tone';
import { MusicMappings, StationConfig, STATION_CONFIGS } from './mapping';
import { 
  NoteEvent, 
  WebSocketMessage, 
  AudioStats
} from './types';
import './App.css';

// Environment variables with fallbacks
const WS_URL = (import.meta as any).env?.VITE_WS_URL || 'ws://localhost:8000/ws/serp';
const API_KEY = (import.meta as any).env?.VITE_API_KEY || 'dev-token-123';

function App() {
  // State
  const [isConnected, setIsConnected] = useState(false);
  const [isAudioStarted, setIsAudioStarted] = useState(false);
  const [currentStation, setCurrentStation] = useState<string>('daily');
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(0.8);
  const [stats, setStats] = useState<AudioStats>({
    activeNotes: 0,
    eventsReceived: 0,
    peakLevel: 0,
    latency: 0
  });
  const [recentEvents, setRecentEvents] = useState<NoteEvent[]>([]);

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const synthRef = useRef<Tone.PolySynth | null>(null);
  const reverbRef = useRef<Tone.Reverb | null>(null);
  const delayRef = useRef<Tone.FeedbackDelay | null>(null);
  const pannerRef = useRef<Tone.Panner | null>(null);
  const meterRef = useRef<Tone.Meter | null>(null);
  const mappingsRef = useRef(new MusicMappings());

  // Audio setup
  const initializeAudio = useCallback(async () => {
    try {
      // Start Tone.js context
      await Tone.start();
      
      // Create audio chain: Synth -> Effects -> Destination
      const synth = new Tone.PolySynth(Tone.AMSynth, {
        oscillator: {
          type: 'triangle'
        },
        envelope: {
          attack: 0.01,
          decay: 0.1,
          sustain: 0.3,
          release: 0.3
        }
      });

      const reverb = new Tone.Reverb(0.3);

      const delay = new Tone.FeedbackDelay({
        delayTime: 0.1,
        feedback: 0.2
      });

      const panner = new Tone.Panner(0);
      const meter = new Tone.Meter();
      const limiter = new Tone.Limiter(-1); // Prevent clipping at -1dBFS

      // Connect audio chain: Synth -> Effects -> Limiter -> Destination
      synth.chain(delay, reverb, panner, limiter, meter, Tone.Destination);

      // Store refs
      synthRef.current = synth;
      reverbRef.current = reverb;
      delayRef.current = delay;
      pannerRef.current = panner;
      meterRef.current = meter;

      setIsAudioStarted(true);
      console.log('Audio system initialized');

    } catch (error) {
      console.error('Failed to initialize audio:', error);
    }
  }, []);

  // WebSocket connection
  const connectWebSocket = useCallback(() => {
    try {
      const url = `${WS_URL}?api_key=${API_KEY}&station=${currentStation}`;
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        
        // Send ping to test connection
        ws.send(JSON.stringify({
          type: 'ping',
          data: { timestamp: new Date().toISOString() }
        }));
      };

      ws.onmessage = async (event) => {
        try {
          let message: WebSocketMessage;

          // Handle binary msgpack data
          if (event.data instanceof ArrayBuffer) {
            // For now, skip msgpack parsing to avoid dependency issues
            console.log('Received binary message');
            return;
          } else {
            // Parse JSON
            message = JSON.parse(event.data) as WebSocketMessage;
          }

          handleWebSocketMessage(message);

        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setIsConnected(false);
        
        // Attempt to reconnect after delay
        setTimeout(() => {
          if (wsRef.current === ws) {
            connectWebSocket();
          }
        }, 3000);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsConnected(false);
      };

      wsRef.current = ws;

    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      setIsConnected(false);
    }
  }, [currentStation]);

  // Handle WebSocket messages
  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'note_event':
        handleNoteEvent(message.data as NoteEvent);
        break;
      case 'station_update':
        handleStationUpdate(message.data);
        break;
      case 'pong':
        // Calculate latency
        const latency = Date.now() - new Date(message.data.timestamp).getTime();
        setStats(prev => ({ ...prev, latency }));
        break;
      default:
        console.log('Unknown message type:', message.type);
    }
  }, []);

  // Handle note events from WebSocket
  const handleNoteEvent = useCallback((event: NoteEvent) => {
    if (!synthRef.current || !isAudioStarted || isMuted) {
      return;
    }

    try {
      // Convert MIDI values to Tone.js parameters
      const mappings = mappingsRef.current;
      
      // Get frequency from rank delta
      const frequency = mappings.getPitchFromRankDelta(event.rank_delta);
      
      // Get velocity (0-1 for Tone.js)
      const velocity = mappings.getVelocityFromShare(event.velocity / 127);
      
      // Set pan position
      if (pannerRef.current) {
        pannerRef.current.pan.value = event.pan;
      }

      // Trigger note
      const duration = `${event.duration}n`; // Convert to Tone.js notation
      synthRef.current.triggerAttackRelease(frequency, duration, Tone.now(), velocity);

      // Update stats
      setStats(prev => ({
        ...prev,
        eventsReceived: prev.eventsReceived + 1,
        activeNotes: prev.activeNotes + 1
      }));

      // Add to recent events
      setRecentEvents(prev => [event, ...prev.slice(0, 9)]);

      // Visual feedback for anomalies
      if (event.anomaly) {
        document.body.style.background = '#ff4444';
        setTimeout(() => {
          document.body.style.background = '';
        }, 200);
      }

    } catch (error) {
      console.error('Error playing note event:', error);
    }
  }, [isAudioStarted, isMuted]);

  // Handle station configuration updates
  const handleStationUpdate = useCallback((stationData: StationConfig) => {
    if (!reverbRef.current || !delayRef.current) return;

    try {
      // Update audio effects based on station config
      reverbRef.current.decay = stationData.reverb;
      delayRef.current.delayTime.value = stationData.delay;
      delayRef.current.feedback.value = stationData.delay * 0.5;

      console.log('Updated station config:', stationData.name);

    } catch (error) {
      console.error('Error updating station config:', error);
    }
  }, []);

  // Change station
  const changeStation = useCallback((newStation: string) => {
    setCurrentStation(newStation);
    
    if (wsRef.current && isConnected) {
      wsRef.current.send(JSON.stringify({
        type: 'station_change',
        data: { station: newStation }
      }));
    }
  }, [isConnected]);

  // Toggle mute
  const toggleMute = useCallback(() => {
    const newMuted = !isMuted;
    setIsMuted(newMuted);
    
    if (synthRef.current) {
      synthRef.current.volume.value = newMuted ? -Infinity : Tone.gainToDb(volume);
    }

    if (wsRef.current && isConnected) {
      wsRef.current.send(JSON.stringify({
        type: 'mute',
        data: { muted: newMuted }
      }));
    }
  }, [isMuted, volume, isConnected]);

  // Change volume
  const changeVolume = useCallback((newVolume: number) => {
    setVolume(newVolume);
    
    if (synthRef.current && !isMuted) {
      synthRef.current.volume.value = Tone.gainToDb(newVolume);
    }

    if (wsRef.current && isConnected) {
      wsRef.current.send(JSON.stringify({
        type: 'volume',
        data: { volume: newVolume }
      }));
    }
  }, [isMuted, isConnected]);

  // Effects
  useEffect(() => {
    connectWebSocket();
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connectWebSocket]);

  // Update peak meter
  useEffect(() => {
    if (!meterRef.current) return;

    const updateMeter = () => {
      if (meterRef.current) {
        const level = meterRef.current.getValue() as number;
        setStats(prev => ({ ...prev, peakLevel: Math.max(0, level + 50) / 50 }));
      }
    };

    const interval = setInterval(updateMeter, 100);
    return () => clearInterval(interval);
  }, [isAudioStarted]);

  // Get current station config
  const currentStationConfig = STATION_CONFIGS.find(s => s.station === currentStation);

  return (
    <div className="app">
      <header className="app-header">
        <h1>🎵 SERP Loop Radio Live</h1>
        <div className="connection-status">
          <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
            {isConnected ? '● Connected' : '○ Disconnected'}
          </span>
        </div>
      </header>

      <main className="app-main">
        {/* Station Selection */}
        <section className="station-section">
          <h2>Station</h2>
          <div className="station-grid">
            {STATION_CONFIGS.map((station) => (
              <button
                key={station.station}
                className={`station-button ${currentStation === station.station ? 'active' : ''}`}
                onClick={() => changeStation(station.station)}
              >
                <div className="station-name">{station.name}</div>
                <div className="station-description">{station.description}</div>
              </button>
            ))}
          </div>
          {currentStationConfig && (
            <div className="station-info">
              <span>Tempo: {currentStationConfig.tempo} BPM</span>
              <span>Scale: {currentStationConfig.scale}</span>
              <span>Key: {currentStationConfig.root_note}</span>
            </div>
          )}
        </section>

        {/* Audio Controls */}
        <section className="audio-controls">
          <h2>Audio</h2>
          <div className="controls-grid">
            {!isAudioStarted ? (
              <button className="start-audio-button" onClick={initializeAudio}>
                🔊 Start Audio
              </button>
            ) : (
              <>
                <button className={`mute-button ${isMuted ? 'muted' : ''}`} onClick={toggleMute}>
                  {isMuted ? '🔇 Unmute' : '🔊 Mute'}
                </button>
                <div className="volume-control">
                  <label>Volume</label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={volume}
                    onChange={(e) => changeVolume(parseFloat(e.target.value))}
                  />
                  <span>{Math.round(volume * 100)}%</span>
                </div>
              </>
            )}
          </div>
        </section>

        {/* Peak Meter */}
        <section className="peak-meter-section">
          <h2>Audio Level</h2>
          <div className="peak-meter">
            <div 
              className="peak-level" 
              style={{ width: `${stats.peakLevel * 100}%` }}
            />
          </div>
        </section>

        {/* Statistics */}
        <section className="stats-section">
          <h2>Statistics</h2>
          <div className="stats-grid">
            <div className="stat">
              <span className="stat-label">Events Received</span>
              <span className="stat-value">{stats.eventsReceived}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Active Notes</span>
              <span className="stat-value">{stats.activeNotes}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Latency</span>
              <span className="stat-value">{stats.latency}ms</span>
            </div>
          </div>
        </section>

        {/* Recent Events */}
        <section className="events-section">
          <h2>Recent Events</h2>
          <div className="events-list">
            {recentEvents.map((event, index) => (
              <div key={`${event.timestamp}-${index}`} className={`event-item ${event.anomaly ? 'anomaly' : ''}`}>
                <div className="event-keyword">{event.keyword}</div>
                <div className="event-domain">{event.domain}</div>
                <div className="event-delta">
                  {event.rank_delta > 0 ? '↓' : event.rank_delta < 0 ? '↑' : '→'} {Math.abs(event.rank_delta)}
                </div>
                <div className="event-engine">{event.engine}</div>
              </div>
            ))}
          </div>
        </section>
      </main>

      <footer className="app-footer">
        <p>SERP Loop Radio Live • Real-time SERP data sonification</p>
        <p>
          <a href="http://localhost:8000" target="_blank" rel="noreferrer">API Server</a> • 
          <a href="http://localhost:8000/health" target="_blank" rel="noreferrer">Health Check</a>
        </p>
      </footer>
    </div>
  );
}

export default App; 