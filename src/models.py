"""
Pydantic v2 models for SERP Radio production FastAPI backend.
"""

import re
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class SonifyRequest(BaseModel):
    """Request model for sonification jobs."""
    
    tenant: str = Field(..., description="Tenant identifier")
    dataset_id: Optional[str] = Field(None, description="CSV dataset identifier")
    lookback: str = Field("1d", description="Time lookback period")
    source: Literal["demo", "gsc", "serp"] = Field("demo", description="Data source")
    use_training: bool = Field(True, description="Use trained model/rules")
    momentum: bool = Field(True, description="Include momentum analysis")
    override_metrics: Optional[Dict[str, Any]] = Field(None, description="Override metrics for testing")
    seed: Optional[int] = Field(None, description="Deterministic seed for reproducible results")
    tempo_base: int = Field(120, description="Base tempo in BPM")
    total_bars: int = Field(32, description="Total number of bars")
    sound_pack: str = Field("Arena Rock", description="Sound pack for generation")
    demo_type: Optional[str] = Field(None, description="Demo type for legacy compatibility")
    
    @field_validator("tenant")
    @classmethod
    def validate_tenant(cls, v: str) -> str:
        """Validate tenant format: lowercase alphanumeric, hyphens, underscores only."""
        if not re.match(r"^[a-z0-9_-]+$", v):
            raise ValueError("Tenant must be lowercase alphanumeric with hyphens/underscores only")
        if len(v) < 2 or len(v) > 50:
            raise ValueError("Tenant must be 2-50 characters")
        return v
    
    @field_validator("lookback")
    @classmethod
    def validate_lookback(cls, v: str) -> str:
        """Validate lookback format: number + unit (d/w/m)."""
        if not re.match(r"^[1-9]\d*[dwm]$", v):
            raise ValueError("Lookback must be format like '1d', '7d', '2w', '1m'")
        return v
    
    @field_validator("override_metrics")
    @classmethod
    def validate_override_metrics(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Validate override metrics; numeric values must be within 0-1."""
        if v is None:
            return v
        
        for key, value in v.items():
            if isinstance(value, (int, float)):
                if not 0.0 <= float(value) <= 1.0:
                    raise ValueError(f"Metric {key} must be in range 0.0-1.0")
            else:
                # Allow structured payloads (e.g., momentum_data arrays)
                continue
        
        return v


class SonifyResponse(BaseModel):
    """Response model for sonification job creation."""
    
    job_id: str = Field(..., description="Unique job identifier")
    status: Literal["queued", "running", "done", "error"] = Field("queued", description="Job status")


class JobStatus(BaseModel):
    """Model for job status and artifacts."""
    
    job_id: str = Field(..., description="Job identifier")
    status: Literal["queued", "running", "done", "error"] = Field(..., description="Current status")
    midi_url: Optional[str] = Field(None, description="Presigned URL to MIDI file")
    mp3_url: Optional[str] = Field(None, description="Presigned URL to MP3 file")
    momentum_json_url: Optional[str] = Field(None, description="Presigned URL to momentum analysis")
    log_url: Optional[str] = Field(None, description="Presigned URL to processing logs")
    error: Optional[str] = Field(None, description="Error message if failed")
    label_summary: Optional[Dict[str, int]] = Field(None, description="Summary of labels used")
    duration_sec: Optional[float] = Field(None, description="Audio duration in seconds")
    sound_pack: Optional[str] = Field(None, description="Sound pack used for generation")
    created_at: Optional[str] = Field(None, description="Job creation timestamp")
    completed_at: Optional[str] = Field(None, description="Job completion timestamp")


class UploadCsvResponse(BaseModel):
    """Response model for CSV upload."""
    
    dataset_id: str = Field(..., description="Unique dataset identifier")
    inferred_schema: Dict[str, str] = Field(..., description="Inferred column types")
    mapping: Dict[str, str] = Field(..., description="Column to metric mapping")
    row_count: int = Field(..., description="Number of rows in dataset")
    preview: List[Dict[str, str]] = Field(..., description="First 5 rows for preview")


class SaveRulesRequest(BaseModel):
    """Request model for saving YAML rules."""
    
    tenant: str = Field(..., description="Tenant identifier")
    yaml_text: str = Field(..., description="YAML rule configuration")
    
    @field_validator("tenant")
    @classmethod
    def validate_tenant(cls, v: str) -> str:
        """Validate tenant format."""
        if not re.match(r"^[a-z0-9_-]+$", v):
            raise ValueError("Tenant must be lowercase alphanumeric with hyphens/underscores only")
        return v
    
    @field_validator("yaml_text")
    @classmethod
    def validate_yaml_size(cls, v: str) -> str:
        """Validate YAML text size limit."""
        if len(v.encode("utf-8")) > 100 * 1024:  # 100KB limit
            raise ValueError("YAML text cannot exceed 100KB")
        if not v.strip():
            raise ValueError("YAML text cannot be empty")
        return v


class SaveRulesResponse(BaseModel):
    """Response model for saving YAML rules."""
    
    version_key: str = Field(..., description="S3 key of saved version")
    tenant: str = Field(..., description="Tenant identifier")
    saved_at: str = Field(..., description="Save timestamp")


class HealthResponse(BaseModel):
    """Health check response model."""
    
    ok: bool = Field(True, description="Service health status")
    version: str = Field("1.0.0", description="API version")
    timestamp: str = Field(..., description="Current timestamp")
    services: Dict[str, str] = Field(..., description="Service status checks")


class ShareResponse(BaseModel):
    """Response model for share link creation."""
    
    share_url: str = Field(..., description="Shareable URL for the job")
    expires_at: str = Field(..., description="Share link expiration timestamp")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, str]] = Field(None, description="Additional error details")
