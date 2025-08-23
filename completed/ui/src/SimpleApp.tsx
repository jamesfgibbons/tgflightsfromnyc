import React, { useState, useEffect, useRef, useCallback } from 'react';
import * as Tone from 'tone';
import { MusicMappings, StationConfig, STATION_CONFIGS } from './mapping';
import { NoteEvent, WebSocketMessage, AudioStats } from './types';
import './App.css';

// Environment variables with fallbacks
const WS_URL = (import.meta as any).env?.VITE_WS_URL || 'ws://localhost:8000/ws/serp';
const API_KEY = (import.meta as any).env?.VITE_API_KEY || 'dev-token-123';

function SimpleApp() {
  // State
  const [keywords, setKeywords] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [isAudioStarted, setIsAudioStarted] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [eventsReceived, setEventsReceived] = useState(0);
  const [currentlyPlaying, setCurrentlyPlaying] = useState<string>('');
  const [isConnected, setIsConnected] = useState(false);
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
  const aiSynthRef = useRef<Tone.PolySynth | null>(null);
  const limiterRef = useRef<Tone.Limiter | null>(null);
  const reverbRef = useRef<Tone.Reverb | null>(null);
  const delayRef = useRef<Tone.FeedbackDelay | null>(null);
  const pannerRef = useRef<Tone.Panner | null>(null);
  const meterRef = useRef<Tone.Meter | null>(null);
  const mappingsRef = useRef(new MusicMappings());

  // Demo keywords for quick test
  const demoKeywords = [
    'ai chatbot',
    'machine learning',
    'cloud computing',
    'digital marketing',
    'seo tools',
    'keyword research',
    'data analytics',
    'web development',
    'mobile apps',
    'cybersecurity'
  ].join('\n');

  // Initialize audio system
  const initializeAudio = useCallback(async () => {
    try {
      await Tone.start();
      
      // Piano synth for regular results
      const pianoSynth = new Tone.PolySynth(Tone.Synth, {
        oscillator: { type: 'triangle' },
        envelope: { attack: 0.01, decay: 0.1, sustain: 0.3, release: 0.5 }
      });

      // Airy synth pad for AI Overview results  
      const aiSynth = new Tone.PolySynth(Tone.Synth, {
        oscillator: { type: 'sine' },
        envelope: { attack: 0.3, decay: 0.2, sustain: 0.6, release: 1.0 }
      });

      // Effects chain
      const reverb = new Tone.Reverb(0.3);
      const delay = new Tone.FeedbackDelay({ delayTime: 0.15, feedback: 0.25 });
      const limiter = new Tone.Limiter(-1); // Prevent clipping

      // Connect audio chain
      pianoSynth.chain(reverb, delay, limiter, Tone.Destination);
      aiSynth.chain(reverb, delay, limiter, Tone.Destination);

      synthRef.current = pianoSynth;
      aiSynthRef.current = aiSynth;
      limiterRef.current = limiter;

      setIsAudioStarted(true);
      console.log('Audio system ready - Piano + AI Synth initialized');

    } catch (error) {
      console.error('Audio initialization failed:', error);
    }
  }, []);

  // Play note based on SERP data
  const playNote = useCallback((event: NoteEvent) => {
    if (!synthRef.current || !aiSynthRef.current || !isAudioStarted) return;

    try {
      // Play the note with proper channel routing
      const synth = synthRef.current; // Use default synth for all events
      
      if (!synth) return;

      // Map velocity (0-127) to Tone.js range (0-1)
      const toneVelocity = Math.max(0.1, Math.min(1.0, event.velocity / 127));
      
      // Map pitch to frequency - use event.pitch directly
      const frequency = Tone.Frequency(event.pitch, "midi").toFrequency();
      
      // Determine duration based on event properties
      let duration = '8n'; // Default eighth note
      // Use domain or other available properties for duration variation
      if (event.domain.includes('youtube')) duration = '4n'; // Longer for video domains
      if (event.domain.includes('shopping')) duration = '16n'; // Shorter for shopping

      // Get pan value from event
      const panValue = event.pan;
      
      // Trigger note
      synth.triggerAttackRelease(frequency, duration, Tone.now(), toneVelocity);
      
      // Visual feedback
      setCurrentlyPlaying(`${event.keyword} (${event.engine})`);
      setTimeout(() => setCurrentlyPlaying(''), 1000);
      
      // Anomaly flash
      if (event.anomaly) {
        document.body.style.background = '#ff6b6b';
        setTimeout(() => { document.body.style.background = ''; }, 300);
      }

    } catch (error) {
      console.error('Error playing note:', error);
    }
  }, [isAudioStarted]);

  // Start streaming session
  const startStreaming = useCallback(async (keywordList: string, isDemo: boolean = false) => {
    if (!isAudioStarted) {
      alert('Please start audio first');
      return;
    }

    setIsStreaming(true);
    setEventsReceived(0);

    try {
      // Create session ID
      const newSessionId = `session_${Date.now()}`;
      setSessionId(newSessionId);

      // Connect WebSocket with session ID
      const url = `${WS_URL}?api_key=${API_KEY}&station=daily&session=${newSessionId}`;
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('Connected to SERP stream');
        
        // Send keywords for processing
        ws.send(JSON.stringify({
          type: 'start_session',
          data: {
            keywords: keywordList.split('\n').filter(k => k.trim()),
            demo_mode: isDemo,
            session_id: newSessionId
          }
        }));
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          if (message.type === 'note_event') {
            const noteEvent = message.data as NoteEvent;
            playNote(noteEvent);
            setEventsReceived(prev => prev + 1);
          }
          
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        console.log('Stream ended');
        setIsStreaming(false);
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setIsStreaming(false);
      };

      wsRef.current = ws;

    } catch (error) {
      console.error('Failed to start streaming:', error);
      setIsStreaming(false);
    }
  }, [isAudioStarted, playNote]);

  // Stop streaming
  const stopStreaming = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    setIsStreaming(false);
    setSessionId(null);
  }, []);

  // Start demo
  const startDemo = useCallback(() => {
    startStreaming(demoKeywords, true);
  }, [startStreaming, demoKeywords]);

  // Start user keywords
  const startUserSession = useCallback(() => {
    const keywordList = keywords.trim();
    if (!keywordList) {
      alert('Please enter some keywords');
      return;
    }

    const keywordCount = keywordList.split('\n').filter(k => k.trim()).length;
    if (keywordCount > 50) {
      alert('Maximum 50 keywords allowed');
      return;
    }

    startStreaming(keywordList, false);
  }, [keywords, startStreaming]);

  return (
    <div className="simple-app">
      <header className="hero-section">
        <h1>🎵 SERP Radio</h1>
        <p className="tagline">
          Hear your search rankings in real-time
        </p>
        <p className="description">
          Paste keywords → Hit play → Listen to rank movements as music
        </p>
      </header>

      <main className="main-content">
        {/* Three Tiers */}
        <section className="tier-section">
          
          {/* Tier 1: Demo */}
          <div className="tier demo-tier">
            <h2>🎧 Demo</h2>
            <p>Hear sample SERP data instantly</p>
            <div className="tier-controls">
              {!isAudioStarted ? (
                <button 
                  className="audio-start-btn"
                  onClick={initializeAudio}
                >
                  🔊 Start Audio System
                </button>
              ) : (
                <button 
                  className="demo-btn"
                  onClick={startDemo}
                  disabled={isStreaming}
                >
                  {isStreaming ? '🎵 Playing Demo...' : '▶️ Play Demo'}
                </button>
              )}
            </div>
          </div>

          {/* Tier 2: Self-serve */}
          <div className="tier selfserve-tier">
            <h2>🎯 Your Keywords</h2>
            <p>Up to 50 keywords • Instant sonification</p>
            <div className="keyword-input">
              <textarea
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
                placeholder={`Enter your keywords (one per line):\n\nartificial intelligence\nmachine learning\ndata science\nseo optimization\n...`}
                rows={8}
                maxLength={2000}
                disabled={isStreaming}
              />
              <div className="input-meta">
                <span>
                  {keywords.split('\n').filter(k => k.trim()).length} / 50 keywords
                </span>
                <span>
                  Cost: ~${(keywords.split('\n').filter(k => k.trim()).length * 0.001).toFixed(3)}
                </span>
              </div>
            </div>
            <button 
              className="stream-btn"
              onClick={startUserSession}
              disabled={!isAudioStarted || isStreaming || !keywords.trim()}
            >
              {isStreaming ? '🎵 Streaming...' : '🚀 Stream Live'}
            </button>
          </div>

          {/* Tier 3: Beta */}
          <div className="tier beta-tier">
            <h2>⭐ Beta Access</h2>
            <p>Daily monitoring • Email alerts • Custom projects</p>
            <button className="beta-btn" disabled>
              Coming Soon
            </button>
          </div>

        </section>

        {/* Live Status */}
        {(isStreaming || eventsReceived > 0) && (
          <section className="status-section">
            <h2>🎵 Live Status</h2>
            <div className="status-grid">
              <div className="status-item">
                <span className="status-label">Session</span>
                <span className="status-value">
                  {isStreaming ? '🔴 Live' : '⏹️ Stopped'}
                </span>
              </div>
              <div className="status-item">
                <span className="status-label">Events</span>
                <span className="status-value">{eventsReceived}</span>
              </div>
              <div className="status-item">
                <span className="status-label">Playing</span>
                <span className="status-value">
                  {currentlyPlaying || 'Waiting...'}
                </span>
              </div>
            </div>
            {isStreaming && (
              <button className="stop-btn" onClick={stopStreaming}>
                ⏹️ Stop Stream
              </button>
            )}
          </section>
        )}

        {/* How it works */}
        <section className="how-it-works">
          <h2>🎼 How It Works</h2>
          <div className="mapping-grid">
            <div className="mapping-item">
              <span className="mapping-label">Rank ↑</span>
              <span className="mapping-value">Higher pitch</span>
            </div>
            <div className="mapping-item">
              <span className="mapping-label">Rank ↓</span>
              <span className="mapping-value">Lower pitch</span>
            </div>
            <div className="mapping-item">
              <span className="mapping-label">Market Share</span>
              <span className="mapping-value">Volume/loudness</span>
            </div>
            <div className="mapping-item">
              <span className="mapping-label">Regular Results</span>
              <span className="mapping-value">Piano notes</span>
            </div>
            <div className="mapping-item">
              <span className="mapping-label">AI Overview</span>
              <span className="mapping-value">Airy synth pad</span>
            </div>
            <div className="mapping-item">
              <span className="mapping-label">Shopping/Video</span>
              <span className="mapping-value">Staccato/Legato</span>
            </div>
          </div>
        </section>

      </main>

      <footer className="app-footer">
        <p>SERP Radio • Powered by DataForSEO API • Real-time SERP sonification</p>
      </footer>
    </div>
  );
}

export default SimpleApp; 