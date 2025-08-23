"""
Pydantic schemas for pipeline IO.
"""
from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field

Label = Literal["positive","neutral","negative"]

class MomentumBand(BaseModel):
    t0: float
    t1: float
    label: Label
    score: float

class LLMFlightResult(BaseModel):
    origin: str
    destination: str
    prompt: str
    estimated_price_range: Optional[List[float]] = None
    best_booking_window: Optional[int] = None
    peak_discount_times: Optional[List[str]] = None
    carrier_likelihood: Optional[List[str]] = None
    routing_strategy: Optional[str] = None  # direct | connecting | hidden-city | multi-city
    novelty_score: Optional[float] = None   # 1-10
    sonification_params: Optional[Dict[str, Any]] = None

class SonifyPlan(BaseModel):
    sound_pack: Literal["Arena Rock","8-Bit","Synthwave","Tropical Pop"] = "Synthwave"
    total_bars: int = 32
    tempo_base: int = 120
    key_hint: Optional[str] = None
    momentum: List[MomentumBand] = Field(default_factory=list)
    label_summary: Dict[str, int] = Field(default_factory=dict)

class CacheEntry(BaseModel):
    id: str
    timestamp: str
    channel: str
    brand: Optional[str] = None
    title: str
    prompt: str
    sound_pack: str
    duration_sec: float
    mp3_url: Optional[str] = None
    midi_url: Optional[str] = None
    momentum_json: List[MomentumBand]
    label_summary: Dict[str,int]
