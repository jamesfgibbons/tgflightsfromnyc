"""
Core VibeNet intermediate representations and API models.

These IRs are intentionally small and serializable so that modules can be
swapped or tested independently: V (vibe vector), H (harmony plan), P (performance).
"""
from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class VibeVector(BaseModel):
    """Continuous vibe axes + discrete tags for palette/meter."""
    valence: float = Field(ge=0.0, le=1.0)
    arousal: float = Field(ge=0.0, le=1.0)
    tension: float = Field(ge=0.0, le=1.0)
    brightness: float = Field(ge=0.0, le=1.0)
    warmth: float = Field(ge=0.0, le=1.0)
    density: float = Field(ge=0.0, le=1.0)
    syncopation: float = Field(ge=0.0, le=1.0)
    harm_complexity: float = Field(ge=0.0, le=1.0)
    palette: str = Field(default="synthwave_midnight")
    meter: Literal["straight_4", "half_time", "12_8"] = Field(default="straight_4")


class HarmonyBar(BaseModel):
    bar: int
    chord: Optional[str] = None
    borrowed: Optional[str] = None
    turn: Optional[bool] = None


class HarmonyPlan(BaseModel):
    key: str
    mode: Literal["ionian", "dorian", "phrygian", "aeolian", "mixolydian"]
    bars: List[HarmonyBar]


class PerformanceCC(BaseModel):
    t: float
    cc: int
    val: int


class PerformanceNote(BaseModel):
    t: float
    dur: float
    pitch: int
    vel: int


class PerformanceTrack(BaseModel):
    name: str
    program: str
    notes: List[PerformanceNote] = Field(default_factory=list)
    cc: List[PerformanceCC] = Field(default_factory=list)


class PerformanceSpec(BaseModel):
    tracks: List[PerformanceTrack] = Field(default_factory=list)
    tempo_bpm: int = 112


class EmbedRequest(BaseModel):
    data: List[float]
    palette: Optional[str] = None


class EmbedResponse(BaseModel):
    vibe: VibeVector


class TrainTake(BaseModel):
    take_id: str
    palette: str
    vibe: VibeVector
    bpm: int
    progression: Optional[List[str]] = None
    midi_key: Optional[str] = Field(default=None, description="Stored MIDI key (S3/R2)")


class TrainRequest(BaseModel):
    takes: List[TrainTake]


class TrainResponse(BaseModel):
    ok: bool
    accepted: int
