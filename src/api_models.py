"""
Uniform API models for SERP Radio backend responses.
All endpoints (jobs, share, preview, hero) use these consistent schemas.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class MomentumBand(BaseModel):
    """A momentum band with timing and classification."""
    t0: float = Field(description="Start time in seconds")
    t1: float = Field(description="End time in seconds") 
    label: Literal["positive", "neutral", "negative"] = Field(description="Momentum classification")
    score: float = Field(description="Confidence score 0.0-1.0")


class LabelSummary(BaseModel):
    """Summary of momentum labels across the piece."""
    positive: int = Field(default=0, description="Count of positive momentum sections")
    neutral: int = Field(default=0, description="Count of neutral momentum sections") 
    negative: int = Field(default=0, description="Count of negative momentum sections")


class JobResult(BaseModel):
    """Uniform response schema for all sonification endpoints."""
    job_id: str = Field(description="Unique job identifier")
    status: Literal["queued", "running", "done", "error"] = Field(description="Job status")
    
    # Audio artifacts
    midi_url: Optional[str] = Field(default=None, description="Presigned URL for MIDI file")
    mp3_url: Optional[str] = Field(default=None, description="Presigned URL for MP3 file")
    duration_sec: Optional[float] = Field(default=None, description="Duration in seconds")
    
    # Sound pack and musical metadata
    sound_pack: str = Field(default="Arena Rock", description="Sound pack used for generation")
    label_summary: LabelSummary = Field(default_factory=LabelSummary, description="Momentum label counts")
    momentum_json: List[MomentumBand] = Field(default_factory=list, description="Detailed momentum analysis")
    
    # Debugging and error handling
    logs: List[str] = Field(default_factory=list, description="Processing logs")
    error_id: Optional[str] = Field(default=None, description="Error identifier if status=error")


class ShareResponse(BaseModel):
    """Response for creating a share link."""
    share_token: str = Field(description="8-character share token")
    share_url: str = Field(description="Full share URL")
    expires_at: str = Field(description="ISO timestamp when share expires")


class HeroStatusPack(BaseModel):
    """Status for a single hero pack."""
    available: bool = Field(description="Whether this pack is available")
    url: Optional[str] = Field(default=None, description="Presigned URL for hero MP3") 
    duration_sec: float = Field(description="Duration in seconds")
    sound_pack: str = Field(description="Pack name")


class HeroStatusResponse(BaseModel):
    """Response for hero status endpoint."""
    packs: dict[str, HeroStatusPack] = Field(description="Status for each available pack")


class SonifyRequest(BaseModel):
    """Request for sonification (demo, preview, or full)."""
    tenant: str = Field(description="Tenant identifier")
    source: Literal["demo", "gsc", "serp"] = Field(default="demo", description="Data source")
    use_training: bool = Field(default=True, description="Whether to use training data")
    momentum: bool = Field(default=True, description="Whether to generate momentum analysis")
    sound_pack: str = Field(default="Arena Rock", description="Sound pack to use")
    
    # For demo mode - override metrics
    override_metrics: Optional[dict] = Field(default=None, description="Override metrics for demo")
    demo_type: Optional[str] = Field(default=None, description="Legacy demo type parameter")
    
    # Advanced options
    seed: Optional[int] = Field(default=None, description="Random seed for reproducible results")
    tempo_base: int = Field(default=120, description="Base tempo in BPM")
    total_bars: int = Field(default=32, description="Total bars to generate")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(description="Health status")
    version: str = Field(description="Application version")
    region: str = Field(description="AWS region or 'local'")
    timestamp: str = Field(description="Current timestamp")