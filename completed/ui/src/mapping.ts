/**
 * Musical mapping utilities for SERP Loop Radio frontend.
 * Mirrors the Python mapping.json configuration for consistent audio mapping.
 */

export interface FATLDMapping {
  pitch: {
    col: string;
    range: [number, number];
    semitone: number;
  };
  velocity: {
    col: string;
    range: [number, number];
    midi: [number, number];
  };
  timbre: {
    col: string;
    map: Record<string, number>;
  };
  pan: {
    col: string;
    map: Record<string, number>;
  };
  duration: {
    col: string;
    map: Record<string, number>;
  };
  bass_riff: {
    enabled: boolean;
    trigger_condition: string;
    file: string;
    root_note: string;
    bpm: number;
    bars: number;
  };
  audio: {
    tempo: number;
    time_signature: [number, number];
    total_bars: number;
    soundfont: string;
  };
  tts: {
    enabled: boolean;
    provider: string;
    voice: string;
    overlay_volume: number;
  };
}

// Default mapping configuration (mirrors config/mapping.json)
export const DEFAULT_MAPPING: FATLDMapping = {
  pitch: {
    col: "rank_delta",
    range: [-10, 10],
    semitone: 1.2
  },
  velocity: {
    col: "share_pct",
    range: [0, 1],
    midi: [40, 127]
  },
  timbre: {
    col: "engine",
    map: {
      "google_web": 0,
      "google_ai": 48,
      "openai": 81,
      "perplexity": 13
    }
  },
  pan: {
    col: "segment",
    map: {
      "West": -30,
      "Central": 0,
      "East": 30
    }
  },
  duration: {
    col: "rich_type",
    map: {
      "shopping_pack": 0.25,
      "video": 0.5,
      "": 1.0
    }
  },
  bass_riff: {
    enabled: true,
    trigger_condition: "brand_rank <= 3",
    file: "assets/jump_riff.mid",
    root_note: "C",
    bpm: 112,
    bars: 8
  },
  audio: {
    tempo: 112,
    time_signature: [4, 4],
    total_bars: 16,
    soundfont: "assets/nice_gm.sf2"
  },
  tts: {
    enabled: false,
    provider: "openai",
    voice: "alloy",
    overlay_volume: 0.3
  }
};

// Musical scales (mirrors Python mappings.py)
export const SCALES: Record<string, number[]> = {
  major: [0, 2, 4, 5, 7, 9, 11],
  minor: [0, 2, 3, 5, 7, 8, 10],
  pentatonic: [0, 2, 4, 7, 9],
  blues: [0, 3, 5, 6, 7, 10],
  dorian: [0, 2, 3, 5, 7, 9, 10]
};

// Note names to MIDI numbers
export const NOTE_TO_MIDI: Record<string, number> = {
  'C': 60, 'C#': 61, 'Db': 61, 'D': 62, 'D#': 63, 'Eb': 63,
  'E': 64, 'F': 65, 'F#': 66, 'Gb': 66, 'G': 67, 'G#': 68,
  'Ab': 68, 'A': 69, 'A#': 70, 'Bb': 70, 'B': 71
};

// Station configurations
export interface StationConfig {
  station: 'daily' | 'ai-lens' | 'opportunity';
  name: string;
  description: string;
  keywords_filter?: string[];
  engine_filter?: string[];
  min_rank_delta?: number;
  tempo: number;
  scale: string;
  root_note: string;
  reverb: number;
  delay: number;
  distortion: number;
}

export const STATION_CONFIGS: StationConfig[] = [
  {
    station: 'daily',
    name: 'Daily SERP Monitor',
    description: 'All SERP changes across tracked keywords',
    tempo: 112,
    scale: 'pentatonic',
    root_note: 'C',
    reverb: 0.2,
    delay: 0.1,
    distortion: 0.0
  },
  {
    station: 'ai-lens',
    name: 'AI Overview Focus',
    description: 'Only AI overview and AI-powered search results',
    engine_filter: ['google_ai', 'openai', 'perplexity'],
    tempo: 90,
    scale: 'minor',
    root_note: 'C',
    reverb: 0.4,
    delay: 0.2,
    distortion: 0.0
  },
  {
    station: 'opportunity',
    name: 'Opportunity Tracker',
    description: 'Large ranking movements and anomalies',
    min_rank_delta: 3,
    tempo: 140,
    scale: 'blues',
    root_note: 'C',
    reverb: 0.2,
    delay: 0.1,
    distortion: 0.1
  }
];

/**
 * Musical mapping utilities class for frontend audio synthesis.
 */
export class MusicMappings {
  private mapping: FATLDMapping;

  constructor(mapping: FATLDMapping = DEFAULT_MAPPING) {
    this.mapping = mapping;
  }

  /**
   * Map a value from input range to output range.
   */
  mapValueToRange(
    value: number,
    inputRange: [number, number],
    outputRange: [number, number],
    clamp: boolean = true
  ): number {
    if (inputRange[1] === inputRange[0]) {
      return outputRange[0];
    }

    // Normalize to 0-1
    let normalized = (value - inputRange[0]) / (inputRange[1] - inputRange[0]);

    if (clamp) {
      normalized = Math.max(0, Math.min(1, normalized));
    }

    // Map to output range
    return outputRange[0] + normalized * (outputRange[1] - outputRange[0]);
  }

  /**
   * Convert rank delta to frequency (Hz) for Tone.js.
   */
  getPitchFromRankDelta(rankDelta: number): number {
    const pitchConfig = this.mapping.pitch;
    const semitones = this.mapValueToRange(
      rankDelta,
      pitchConfig.range,
      [-12, 12] // +/- one octave
    );

    // Convert semitones to frequency ratio
    const baseFreq = 440; // A4
    const frequency = baseFreq * Math.pow(2, (semitones * pitchConfig.semitone) / 12);
    
    return Math.max(80, Math.min(2000, frequency)); // Clamp to reasonable audio range
  }

  /**
   * Convert share percentage to velocity (0-1 for Tone.js).
   */
  getVelocityFromShare(sharePct: number): number {
    const velocityConfig = this.mapping.velocity;
    const velocity = this.mapValueToRange(sharePct, velocityConfig.range, [0, 1]);
    return Math.max(0.1, Math.min(1.0, velocity));
  }

  /**
   * Get oscillator type from search engine.
   */
  getOscillatorFromEngine(engine: string): string {
    const timbreConfig = this.mapping.timbre;
    const instrumentNum = timbreConfig.map[engine] || 0;

    // Map MIDI instrument numbers to Tone.js oscillator types
    const oscillatorMap: Record<number, string> = {
      0: 'triangle',      // Piano -> Triangle
      13: 'square',       // Xylophone -> Square
      48: 'sawtooth',     // Strings -> Sawtooth
      81: 'pulse',        // Lead synth -> Pulse
      104: 'sine'         // Sitar -> Sine
    };

    return oscillatorMap[instrumentNum] || 'triangle';
  }

  /**
   * Get stereo pan position from geographic segment.
   */
  getPanFromSegment(segment: string): number {
    const panConfig = this.mapping.pan;
    const panValue = panConfig.map[segment] || 0;
    return Math.max(-1.0, Math.min(1.0, panValue / 100)); // Convert to -1 to 1 range
  }

  /**
   * Get note duration from rich snippet type.
   */
  getDurationFromRichType(richType: string): number {
    const durationConfig = this.mapping.duration;
    const duration = durationConfig.map[richType] || 1.0;
    return Math.max(0.1, Math.min(4.0, duration));
  }

  /**
   * Get scale notes for a given root and scale type.
   */
  getScaleNotes(rootNote: string = 'C', scale: string = 'pentatonic'): number[] {
    const rootMidi = NOTE_TO_MIDI[rootNote] || 60;
    const scaleIntervals = SCALES[scale] || SCALES.pentatonic;
    
    return scaleIntervals ? scaleIntervals.map(interval => rootMidi + interval) : [];
  }

  /**
   * Fit a frequency to the closest note in a scale.
   */
  fitToScale(frequency: number, scaleNotes: number[]): number {
    if (scaleNotes.length === 0) return frequency;

    // Convert frequency to MIDI note number
    const midiNote = 69 + 12 * Math.log2(frequency / 440);
    
    // Find closest note in scale
    const closestMidi = scaleNotes.reduce((prev, curr) => 
      Math.abs(curr - midiNote) < Math.abs(prev - midiNote) ? curr : prev
    );

    // Convert back to frequency
    return 440 * Math.pow(2, (closestMidi - 69) / 12);
  }

  /**
   * Get station configuration by name.
   */
  getStationConfig(station: string): StationConfig | undefined {
    return STATION_CONFIGS.find(config => config.station === station);
  }
}

/**
 * Factory function to create MusicMappings instance.
 */
export function createMappings(mapping?: FATLDMapping): MusicMappings {
  return new MusicMappings(mapping);
}

export default MusicMappings; 