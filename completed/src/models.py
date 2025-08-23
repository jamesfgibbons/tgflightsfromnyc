"""
Pydantic models for SERP Loop Radio live streaming.
Defines data structures for WebSocket events and real-time audio mapping.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field


class NoteEvent(BaseModel):
    """Real-time note event for WebSocket streaming."""
    
    event_type: Literal["note_on", "note_off", "control_change"] = "note_on"
    pitch: int = Field(..., ge=0, le=127, description="MIDI pitch (0-127)")
    velocity: int = Field(..., ge=0, le=127, description="MIDI velocity (0-127)")
    pan: float = Field(..., ge=-1.0, le=1.0, description="Stereo pan (-1.0 to 1.0)")
    duration: float = Field(..., gt=0, le=8.0, description="Note duration in seconds")
    instrument: int = Field(default=0, ge=0, le=127, description="MIDI instrument number")
    channel: int = Field(default=0, ge=0, le=15, description="MIDI channel")
    
    # Context data
    keyword: str = Field(..., description="Source keyword")
    engine: str = Field(..., description="Search engine")
    domain: str = Field(..., description="Result domain")
    rank_delta: int = Field(..., description="Ranking change")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Additional metadata
    anomaly: bool = Field(default=False, description="Whether this is an anomaly event")
    brand_rank: Optional[int] = Field(default=None, description="Brand ranking if applicable")


class ControlEvent(BaseModel):
    """Control change event for real-time parameter updates."""
    
    event_type: Literal["control_change"] = "control_change"
    controller: int = Field(..., ge=0, le=127, description="MIDI controller number")
    value: int = Field(..., ge=0, le=127, description="Controller value")
    channel: int = Field(default=0, ge=0, le=15, description="MIDI channel")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SERPSnapshot(BaseModel):
    """Snapshot of SERP data for diffing changes."""
    
    keyword: str
    domain: str
    rank_absolute: int
    engine: str
    share_pct: float
    rich_type: str
    segment: str
    ai_overview: bool
    etv: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    def diff_key(self) -> str:
        """Generate unique key for diffing."""
        return f"{self.keyword}:{self.domain}:{self.engine}"


class LiveSession(BaseModel):
    """Live streaming session information."""
    
    session_id: str
    api_key: str
    connected_at: datetime = Field(default_factory=datetime.utcnow)
    station: Literal["daily", "ai-lens", "opportunity"] = "daily"
    muted: bool = False
    volume: float = Field(default=0.8, ge=0.0, le=1.0)
    
    # Statistics
    events_sent: int = 0
    events_received: int = 0
    last_activity: datetime = Field(default_factory=datetime.utcnow)


class StationConfig(BaseModel):
    """Configuration for different audio stations."""
    
    station: Literal["daily", "ai-lens", "opportunity"]
    name: str
    description: str
    keywords_filter: Optional[List[str]] = None
    engine_filter: Optional[List[str]] = None
    min_rank_delta: Optional[int] = None
    
    # Audio settings
    tempo: int = Field(default=112, ge=60, le=200)
    scale: str = Field(default="pentatonic")
    root_note: str = Field(default="C")
    
    # Effects
    reverb: float = Field(default=0.2, ge=0.0, le=1.0)
    delay: float = Field(default=0.1, ge=0.0, le=1.0)
    distortion: float = Field(default=0.0, ge=0.0, le=1.0)


class WebSocketMessage(BaseModel):
    """Wrapper for all WebSocket messages."""
    
    type: Literal["note_event", "control_event", "station_update", "error", "ping", "pong"]
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None


class AudioStats(BaseModel):
    """Real-time audio statistics."""
    
    active_notes: int = 0
    events_per_second: float = 0.0
    peak_level: float = 0.0
    rms_level: float = 0.0
    cpu_usage: float = 0.0
    latency_ms: float = 0.0
    
    # Session stats
    total_events: int = 0
    session_duration: float = 0.0
    dropped_events: int = 0
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorEvent(BaseModel):
    """Error event for WebSocket communication."""
    
    event_type: Literal["error"] = "error"
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Station configurations
DEFAULT_STATIONS: List[StationConfig] = [
    StationConfig(
        station="daily",
        name="Daily SERP Monitor",
        description="All SERP changes across tracked keywords",
        tempo=112,
        scale="pentatonic",
        reverb=0.2
    ),
    StationConfig(
        station="ai-lens",
        name="AI Overview Focus", 
        description="Only AI overview and AI-powered search results",
        engine_filter=["google_ai", "openai", "perplexity"],
        tempo=90,
        scale="minor",
        reverb=0.4,
        delay=0.2
    ),
    StationConfig(
        station="opportunity",
        name="Opportunity Tracker",
        description="Large ranking movements and anomalies",
        min_rank_delta=3,
        tempo=140,
        scale="blues",
        distortion=0.1
    )
]


def get_station_config(station: str) -> StationConfig:
    """Get configuration for a specific station."""
    for config in DEFAULT_STATIONS:
        if config.station == station:
            return config
    
    # Return default if not found
    return DEFAULT_STATIONS[0]


# Export commonly used types
__all__ = [
    "NoteEvent",
    "ControlEvent", 
    "SERPSnapshot",
    "LiveSession",
    "StationConfig",
    "WebSocketMessage",
    "AudioStats",
    "ErrorEvent",
    "DEFAULT_STATIONS",
    "get_station_config"
] 