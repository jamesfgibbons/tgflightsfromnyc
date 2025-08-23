/**
 * TypeScript interfaces for SERP Loop Radio live streaming.
 * Mirrors the Python Pydantic models for consistency.
 */

export interface NoteEvent {
  event_type: "note_on" | "note_off" | "control_change";
  pitch: number; // 0-127 MIDI range
  velocity: number; // 0-127 MIDI range
  pan: number; // -1.0 to 1.0 stereo position
  duration: number; // Note duration in seconds
  instrument: number; // MIDI instrument number
  channel: number; // MIDI channel 0-15
  
  // SERP context data
  keyword: string;
  engine: string;
  domain: string;
  rank_delta: number;
  timestamp: string; // ISO datetime string
  
  // Additional metadata
  anomaly: boolean;
  brand_rank?: number;
  is_new?: boolean;
  stations?: string[];
}

export interface WebSocketMessage {
  type: "note_event" | "station_update" | "connection" | "pong" | "error";
  data: any;
  timestamp: string;
  session_id?: string;
}

export interface StationUpdateData {
  station: string;
  name: string;
  description: string;
  tempo: number;
  scale: string;
  root_note: string;
  reverb: number;
  delay: number;
  distortion: number;
}

export interface AudioStats {
  activeNotes: number;
  eventsReceived: number;
  peakLevel: number; // 0-1 normalized
  latency: number; // milliseconds
}

export interface ConnectionData {
  session_id: string;
  station: string;
  message: string;
}

export interface ErrorData {
  error_code: string;
  message: string;
  details?: Record<string, any>;
}

// Audio engine types
export interface AudioEngine {
  synth: any; // Tone.PolySynth
  reverb: any; // Tone.Reverb
  delay: any; // Tone.FeedbackDelay
  panner: any; // Tone.Panner
  meter: any; // Tone.Meter
}

// Client message types for sending to server
export interface ClientMessage {
  type: "ping" | "station_change" | "mute" | "volume";
  data: Record<string, any>;
}

export interface PingMessage extends ClientMessage {
  type: "ping";
  data: {
    timestamp: string;
  };
}

export interface StationChangeMessage extends ClientMessage {
  type: "station_change";
  data: {
    station: string;
  };
}

export interface MuteMessage extends ClientMessage {
  type: "mute";
  data: {
    muted: boolean;
  };
}

export interface VolumeMessage extends ClientMessage {
  type: "volume";
  data: {
    volume: number;
  };
}

// Environment configuration
export interface EnvironmentConfig {
  WS_URL: string;
  API_KEY: string;
}

// Export types for convenience
export type StationName = "daily" | "ai-lens" | "opportunity";
export type EventType = "note_on" | "note_off" | "control_change";
export type MessageType = "note_event" | "station_update" | "connection" | "pong" | "error";
export type ClientMessageType = "ping" | "station_change" | "mute" | "volume"; 