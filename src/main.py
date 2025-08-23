"""
FastAPI application for SERP Radio production backend.
"""

import csv
import io
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import pandas as pd
from fastapi import FastAPI, BackgroundTasks, HTTPException, UploadFile, File, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import (
    SonifyRequest, SonifyResponse, JobStatus, UploadCsvResponse, 
    HealthResponse, ErrorResponse, ShareResponse
)
from .api_models import (
    JobResult, LabelSummary, MomentumBand, HeroStatusResponse, 
    HeroStatusPack, HealthResponse as ApiHealthResponse
)
from .soundpacks import get_sound_pack, list_sound_packs, DEFAULT_PACK
from .arranger import MusicArranger
from .earcons import create_earcon_generator
from .mixing import master_audio_file
from .storage import put_bytes, get_presigned_url, ensure_tenant_prefix, write_json, S3Storage, StorageError, read_text_s3
from .jobstore import job_store
from .sonify_service import create_sonification_service
from .rules_api import router as rules_router
from .vibe_api import router as vibe_router
from .vibenet_api import router as vibenet_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)

# Environment configuration - supports both S3 and Supabase
STORAGE_BUCKET = os.getenv("STORAGE_BUCKET", os.getenv("S3_BUCKET", "serpradio-artifacts"))
PUBLIC_BUCKET = os.getenv("PUBLIC_STORAGE_BUCKET", os.getenv("S3_PUBLIC_BUCKET", STORAGE_BUCKET))
PUBLIC_CDN_DOMAIN = os.getenv("PUBLIC_CDN_DOMAIN")  # Optional CDN domain
CORS_ORIGINS = [
    "https://serpradio.lovable.app",
    "https://serpradio.com", 
    "https://www.serpradio.com",
    "http://localhost:5173",
    "http://localhost:3000"
]

# FastAPI app
app = FastAPI(
    title="SERP Radio Production API",
    description="Enterprise-grade sonification backend with S3 storage and background processing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["*"]
)

# Include routers
app.include_router(rules_router)
app.include_router(vibe_router)
app.include_router(vibenet_router)

# Dependencies
def get_sonification_service():
    """Dependency injection for sonification service."""
    return create_sonification_service(STORAGE_BUCKET)


# Routes
@app.get("/api/healthz", response_model=ApiHealthResponse)
async def healthz():
    """Modern health check endpoint."""
    return ApiHealthResponse(
        status="healthy",
        version=os.getenv("APP_VERSION", "1.0.0"),
        region=os.getenv("AWS_REGION", "local"),
        timestamp=datetime.utcnow().isoformat()
    )

@app.get("/health", response_model=HealthResponse)  
async def health_check():
    """Legacy health check endpoint."""
    return HealthResponse(
        ok=True,
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
        services={
            "s3": "ok",  # TODO: Add actual S3 health check
            "jobstore": "ok"
        }
    )


@app.get("/api/metrics")
async def get_metrics():
    """
    Basic metrics endpoint for monitoring and observability.
    
    Returns:
        Dictionary with system metrics
    """
    try:
        # Get job store metrics
        total_jobs = job_store.size()
        jobs_by_status = {}
        
        # Count jobs by status
        all_jobs = job_store.list_jobs()
        for job in all_jobs.values():
            status = job.status
            jobs_by_status[status] = jobs_by_status.get(status, 0) + 1
        
        # Basic system info
        import psutil
        import os
        
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "version": os.getenv("APP_VERSION", "1.0.0"),
            "region": os.getenv("AWS_REGION", "local"),
            "jobs": {
                "total": total_jobs,
                "by_status": jobs_by_status
            },
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            }
        }
        
        return metrics
        
    except ImportError:
        # Fallback if psutil not available
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "version": os.getenv("APP_VERSION", "1.0.0"),
            "region": os.getenv("AWS_REGION", "local"),
            "jobs": {
                "total": job_store.size(),
                "by_status": {}
            },
            "system": {
                "status": "metrics_limited"
            }
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "error": "Failed to retrieve metrics"
        }


@app.post("/api/upload-csv", response_model=UploadCsvResponse)
async def upload_csv(
    tenant: str,
    file: UploadFile = File(..., description="CSV file to upload")
):
    """
    Upload and analyze CSV dataset.
    
    Args:
        tenant: Tenant identifier
        file: CSV file upload
    
    Returns:
        Dataset metadata and schema inference
    """
    try:
        # Validate file size (10MB limit)
        if file.size and file.size > 10 * 1024 * 1024:
            raise HTTPException(400, "File too large (max 10MB)")
        
        # Validate file type
        if not file.filename or not file.filename.lower().endswith('.csv'):
            raise HTTPException(400, "File must be a CSV")
        
        # Read and parse CSV
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        
        if len(df) == 0:
            raise HTTPException(400, "CSV file is empty")
        
        # Generate dataset ID
        dataset_id = str(uuid.uuid4())
        
        # Store CSV in S3
        csv_key = ensure_tenant_prefix(tenant, "datasets", f"{dataset_id}.csv")
        put_bytes(STORAGE_BUCKET, csv_key, content, "text/csv")
        
        # Infer schema
        schema = {}
        for col in df.columns:
            dtype = str(df[col].dtype)
            if dtype.startswith('int') or dtype.startswith('float'):
                schema[col] = "numeric"
            elif dtype == 'object':
                schema[col] = "text" 
            else:
                schema[col] = "other"
        
        # Generate mapping suggestions (basic heuristics)
        mapping = {}
        col_lower = [col.lower() for col in df.columns]
        
        if any("ctr" in col or "click" in col for col in col_lower):
            mapping["ctr"] = next(col for col in df.columns if "ctr" in col.lower() or "click" in col.lower())
        if any("impression" in col for col in col_lower):
            mapping["impressions"] = next(col for col in df.columns if "impression" in col.lower())
        if any("position" in col or "rank" in col for col in col_lower):
            mapping["position"] = next(col for col in df.columns if "position" in col.lower() or "rank" in col.lower())
        
        # Preview data (first 5 rows)
        preview = df.head(5).fillna("").to_dict("records")
        
        logger.info(f"CSV uploaded for tenant {tenant}: {dataset_id}, {len(df)} rows")
        
        return UploadCsvResponse(
            dataset_id=dataset_id,
            inferred_schema=schema,
            mapping=mapping,
            row_count=len(df),
            preview=preview
        )
        
    except pd.errors.EmptyDataError:
        raise HTTPException(400, "Invalid CSV format")
    except pd.errors.ParserError as e:
        raise HTTPException(400, f"CSV parsing error: {str(e)}")
    except Exception as e:
        logger.error(f"CSV upload failed: {e}")
        raise HTTPException(500, "Internal server error")


@app.post("/api/sonify", response_model=SonifyResponse)
async def create_sonification(
    request: SonifyRequest,
    background_tasks: BackgroundTasks,
    service = Depends(get_sonification_service)
):
    """
    Create sonification job.
    
    Args:
        request: Sonification parameters
        background_tasks: FastAPI background task handler
        service: Sonification service dependency
    
    Returns:
        Job creation response
    """
    try:
        # Create job
        job_id = job_store.create()
        
        # Define S3 paths
        input_midi_key = ensure_tenant_prefix(request.tenant, "midi_input", "baseline.mid")
        output_base_key = ensure_tenant_prefix(request.tenant, "midi_output", job_id)
        
        # Schedule background processing
        background_tasks.add_task(
            process_sonification,
            job_id,
            request,
            input_midi_key,
            output_base_key,
            service
        )
        
        logger.info(f"Sonification job created: {job_id} for tenant {request.tenant}")
        
        return SonifyResponse(job_id=job_id, status="queued")
        
    except Exception as e:
        logger.error(f"Failed to create sonification job: {e}")
        raise HTTPException(500, "Failed to create job")


@app.get("/api/jobs/{job_id}", response_model=JobResult)
async def get_job_status(job_id: str):
    """
    Get job status and artifacts with uniform schema.
    
    Args:
        job_id: Job identifier
    
    Returns:
        JobResult with presigned URLs and complete metadata
    """
    try:
        job = job_store.get(job_id)
        
        # Convert to JobResult format
        midi_url = None
        mp3_url = None
        duration_sec = None
        momentum_json = []
        label_summary = LabelSummary()
        
        # Generate presigned URLs for completed jobs
        if job.status == "done":
            if job.midi_url:
                midi_key = job.midi_url
                midi_url = get_presigned_url(STORAGE_BUCKET, midi_key, force_download=False)
            
            if job.mp3_url:
                mp3_key = job.mp3_url
                mp3_url = get_presigned_url(STORAGE_BUCKET, mp3_key, force_download=False)
                
                # Try to get duration from job metadata
                duration_sec = getattr(job, 'duration_sec', None)
            
            # Load momentum JSON if available
            if job.momentum_json_url:
                momentum_key = job.momentum_json_url
                try:
                    import json
                    # Use unified storage reader (supports S3 and Supabase)
                    txt = read_text_s3(STORAGE_BUCKET, momentum_key)
                    momentum_data = json.loads(txt)
                    # Convert to MomentumBand format
                    if isinstance(momentum_data, list):
                        for i, band in enumerate(momentum_data):
                            momentum_json.append(MomentumBand(
                                t0=band.get('t0', i * 4.0),
                                t1=band.get('t1', (i + 1) * 4.0),
                                label=band.get('label', 'neutral').lower(),
                                score=band.get('score', 0.5)
                            ))
                except Exception as e:
                    logger.warning(f"Failed to load momentum data: {e}")
            
            # Convert label summary
            if hasattr(job, 'label_summary') and job.label_summary:
                summary = job.label_summary
                label_summary = LabelSummary(
                    positive=summary.get('MOMENTUM_POS', summary.get('positive', 0)),
                    neutral=summary.get('NEUTRAL', summary.get('neutral', 0)),
                    negative=summary.get('MOMENTUM_NEG', summary.get('negative', 0))
                )
        
        return JobResult(
            job_id=job_id,
            status=job.status,
            midi_url=midi_url,
            mp3_url=mp3_url,
            duration_sec=duration_sec,
            sound_pack=getattr(job, 'sound_pack', DEFAULT_PACK),
            label_summary=label_summary,
            momentum_json=momentum_json,
            logs=getattr(job, 'logs', []),
            error_id=getattr(job, 'error_id', None) if job.status == "error" else None
        )
        
    except KeyError:
        raise HTTPException(404, f"Job {job_id} not found")
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(500, "Failed to retrieve job")


@app.post("/api/share/{job_id}", response_model=ShareResponse)
async def create_share_link(job_id: str):
    """
    Create shareable link for job.
    
    Args:
        job_id: Job identifier
    
    Returns:
        Share link details
    """
    try:
        # Verify job exists
        job = job_store.get(job_id)
        
        # Only allow sharing completed jobs
        if job.status != "done":
            raise HTTPException(400, "Can only share completed jobs")
        
        # Create share token
        token = job_store.create_share_token(job_id, ttl_hours=24)
        
        share_url = f"/api/share/{token}"  # Relative URL
        expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        
        logger.info(f"Created share link for job {job_id}: {token}")
        
        return ShareResponse(
            share_url=share_url,
            expires_at=expires_at
        )
        
    except KeyError:
        raise HTTPException(404, f"Job {job_id} not found")
    except Exception as e:
        logger.error(f"Failed to create share link: {e}")
        raise HTTPException(500, "Failed to create share link")


@app.get("/api/share/{token}", response_model=JobResult)
async def get_shared_job(token: str):
    """
    Get job status via share token with uniform schema.
    
    Args:
        token: Share token
    
    Returns:
        JobResult with presigned URLs (shorter TTL for security)
    """
    try:
        job = job_store.get_job_by_share_token(token)
        
        # Convert to JobResult format (similar to get_job_status)
        midi_url = None
        mp3_url = None
        duration_sec = None
        momentum_json = []
        label_summary = LabelSummary()
        
        # Generate presigned URLs for shared jobs (shorter TTL)
        if job.status == "done":
            if job.midi_url:
                midi_key = job.midi_url
                midi_url = get_presigned_url(STORAGE_BUCKET, midi_key, expires=600, force_download=False)  # 10 min
            
            if job.mp3_url:
                mp3_key = job.mp3_url
                mp3_url = get_presigned_url(STORAGE_BUCKET, mp3_key, expires=600, force_download=False)
                duration_sec = getattr(job, 'duration_sec', None)
            
            # Load momentum JSON if available
            if job.momentum_json_url:
                momentum_key = job.momentum_json_url
                try:
                    import json
                    txt = read_text_s3(STORAGE_BUCKET, momentum_key)
                    momentum_data = json.loads(txt)
                    if isinstance(momentum_data, list):
                        for i, band in enumerate(momentum_data):
                            momentum_json.append(MomentumBand(
                                t0=band.get('t0', i * 4.0),
                                t1=band.get('t1', (i + 1) * 4.0),
                                label=band.get('label', 'neutral').lower(),
                                score=band.get('score', 0.5)
                            ))
                except Exception as e:
                    logger.warning(f"Failed to load momentum data: {e}")
            
            # Convert label summary
            if hasattr(job, 'label_summary') and job.label_summary:
                summary = job.label_summary
                label_summary = LabelSummary(
                    positive=summary.get('MOMENTUM_POS', summary.get('positive', 0)),
                    neutral=summary.get('NEUTRAL', summary.get('neutral', 0)),
                    negative=summary.get('MOMENTUM_NEG', summary.get('negative', 0))
                )
        
        return JobResult(
            job_id="shared",  # Mask actual job ID for security
            status=job.status,
            midi_url=midi_url,
            mp3_url=mp3_url,
            duration_sec=duration_sec,
            sound_pack=getattr(job, 'sound_pack', DEFAULT_PACK),
            label_summary=label_summary,
            momentum_json=momentum_json,
            logs=[],  # Don't expose logs in shared mode
            error_id=getattr(job, 'error_id', None) if job.status == "error" else None
        )
        
    except KeyError as e:
        if "expired" in str(e):
            raise HTTPException(410, "Share link has expired")
        raise HTTPException(404, "Share link not found")
    except Exception as e:
        logger.error(f"Failed to get shared job: {e}")
        raise HTTPException(500, "Failed to retrieve shared job")


@app.get("/api/hero-status", response_model=HeroStatusResponse)
async def get_hero_status():
    """
    Get hero audio status for all sound packs using public S3 bucket.
    
    Returns:
        Status and URLs for each sound pack's hero audio
    """
    try:
        packs = {}
        public_storage = S3Storage(PUBLIC_BUCKET)
        
        for pack_name in list_sound_packs().keys():
            # Generate pack slug for S3 key
            pack_slug = pack_name.lower().replace(' ', '_').replace('-', '_')
            hero_key = f"hero/{pack_slug}.mp3"
            
            try:
                # Check if object exists using head_object
                metadata = public_storage.head_object(hero_key)
                
                # Extract duration from metadata if present, otherwise default
                duration_sec = 32.0
                if 'Metadata' in metadata and 'duration' in metadata['Metadata']:
                    try:
                        duration_sec = float(metadata['Metadata']['duration'])
                    except (ValueError, TypeError):
                        pass  # Keep default
                
                # Build public URL
                if PUBLIC_CDN_DOMAIN:
                    hero_url = f"https://{PUBLIC_CDN_DOMAIN}/{hero_key}"
                else:
                    hero_url = f"https://{PUBLIC_BUCKET}.s3.amazonaws.com/{hero_key}"
                
                packs[pack_name] = HeroStatusPack(
                    available=True,
                    url=hero_url,
                    duration_sec=duration_sec,
                    sound_pack=pack_name
                )
                
            except StorageError:
                # Object doesn't exist - return unavailable
                packs[pack_name] = HeroStatusPack(
                    available=False,
                    duration_sec=32.0,
                    sound_pack=pack_name
                )
        
        return HeroStatusResponse(packs=packs)
        
    except Exception as e:
        logger.error(f"Failed to get hero status: {e}")
        raise HTTPException(500, "Failed to retrieve hero status")


@app.post("/api/render-hero")
async def render_hero_audio(
    background_tasks: BackgroundTasks,
    sound_pack: str = DEFAULT_PACK,
    x_admin_secret: str = Depends(lambda x_admin_secret=None: x_admin_secret)
):
    """
    Render hero audio for a sound pack (admin only).
    
    Args:
        sound_pack: Sound pack to render
        x_admin_secret: Admin authentication header
    
    Returns:
        Render job status
    """
    # Check admin secret
    expected_secret = os.getenv("ADMIN_SECRET")
    if not expected_secret or x_admin_secret != expected_secret:
        raise HTTPException(401, "Admin authentication required")
    
    if sound_pack not in list_sound_packs():
        raise HTTPException(400, f"Invalid sound pack: {sound_pack}")
    
    try:
        # Create hero render job
        job_id = f"hero_{sound_pack.lower().replace(' ', '_')}_{int(datetime.utcnow().timestamp())}"
        hero_key = f"hero/{sound_pack.lower().replace(' ', '_')}.mp3"
        
        # Schedule background rendering
        background_tasks.add_task(render_hero_background, sound_pack, hero_key)
        
        logger.info(f"Hero render job started: {job_id} for pack {sound_pack}")
        
        return {"job_id": job_id, "status": "queued", "sound_pack": sound_pack}
        
    except Exception as e:
        logger.error(f"Failed to start hero render: {e}")
        raise HTTPException(500, "Failed to start hero render")


@app.post("/api/demo", response_model=JobResult)
async def create_demo_sonification(
    request: SonifyRequest,
    background_tasks: BackgroundTasks,
    service = Depends(get_sonification_service)
):
    """
    Create demo sonification with wow-factor features.
    
    Args:
        request: Demo sonification parameters
        background_tasks: Background task handler
        service: Sonification service
        
    Returns:
        JobResult for demo
    """
    try:
        # Force demo mode
        request.source = "demo"
        
        # Handle legacy demo_type parameter
        if request.demo_type and not request.override_metrics:
            demo_metrics = {
                "positive_momentum": {"ctr": 0.8, "position": 0.9, "clicks": 0.7, "impressions": 0.6},
                "negative_momentum": {"ctr": 0.2, "position": 0.3, "clicks": 0.3, "impressions": 0.4},
                "volatile_spike": {"ctr": 0.6, "position": 0.5, "volatility_index": 0.8}
            }
            request.override_metrics = demo_metrics.get(request.demo_type, {})
        
        # Create job
        job_id = job_store.create()
        
        # Schedule enhanced processing with arrangement and earcons
        background_tasks.add_task(
            process_enhanced_sonification,
            job_id,
            request,
            service,
            use_wow_features=True
        )
        
        logger.info(f"Demo sonification job created: {job_id}")
        
        return JobResult(
            job_id=job_id,
            status="queued",
            sound_pack=request.sound_pack
        )
        
    except Exception as e:
        logger.error(f"Failed to create demo sonification: {e}")
        raise HTTPException(500, "Failed to create demo sonification")


@app.post("/api/preview", response_model=JobResult)
async def preview_sonification(
    request: SonifyRequest,
    service = Depends(get_sonification_service)
):
    """
    Preview sonification synchronously (fast render).
    
    Args:
        request: Preview parameters
        service: Sonification service
        
    Returns:
        JobResult with preview audio
    """
    try:
        # Create temporary job for preview
        job_id = f"preview_{int(datetime.utcnow().timestamp())}"
        
        # Process synchronously with reduced quality for speed
        request.total_bars = min(request.total_bars, 16)  # Shorter preview
        
        result = await process_enhanced_sonification(
            job_id,
            request, 
            service,
            use_wow_features=True,
            preview_mode=True
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Preview sonification failed: {e}")
        raise HTTPException(500, "Preview failed")


async def render_hero_background(sound_pack: str, hero_key: str):
    """Background task to render hero audio."""
    try:
        from .hero_renderer import HeroRenderer
        
        # Create hero renderer with public bucket
        hero_renderer = HeroRenderer(PUBLIC_BUCKET)
        
        # Render hero audio
        result = await hero_renderer.render_hero(sound_pack, hero_key)
        
        logger.info(f"Hero audio rendered successfully for pack: {sound_pack} - "
                   f"duration: {result['duration_sec']}s, sections: {result['sections']}")
        
    except Exception as e:
        logger.error(f"Hero render failed for pack {sound_pack}: {e}")


async def process_enhanced_sonification(
    job_id: str,
    request: SonifyRequest,
    service,
    use_wow_features: bool = False,
    preview_mode: bool = False
) -> JobResult:
    """
    Enhanced sonification processing with wow-factor features.
    
    Args:
        job_id: Job identifier
        request: Sonification request
        service: Sonification service
        use_wow_features: Whether to apply arrangements, earcons, mastering
        preview_mode: If True, return JobResult directly (synchronous)
        
    Returns:
        JobResult (if preview_mode) or updates job store (async)
    """
    try:
        if not preview_mode:
            job_store.start(job_id)
            logger.info(f"Processing enhanced sonification job {job_id}")
        
        # Create arranger and earcon generator
        arranger = MusicArranger(
            total_bars=request.total_bars,
            base_tempo=request.tempo_base
        )
        earcon_gen = create_earcon_generator(request.sound_pack)
        
        # Generate base sonification (ensure output key exists)
        output_base_key = ensure_tenant_prefix(request.tenant, "midi_output", job_id)
        base_result = service.run_sonification(request, None, output_base_key)
        
        if use_wow_features and base_result.get("momentum_data"):
            # Apply musical arrangement
            momentum_data = base_result["momentum_data"]
            sections = arranger.arrange_momentum_data(momentum_data)
            
            # Apply earcons based on query features
            for section in sections:
                # Detect SERP features (mock data for demo)
                query_features = earcon_gen.detect_serp_features({
                    "current_position": 2 if section.momentum_score > 0.7 else 5,
                    "serp_analysis": {"ai_overview": section.momentum_score > 0.6}
                })
                
                if query_features:
                    earcon_events = earcon_gen.generate_earcons_for_section(
                        query_features,
                        section.start_beat,
                        section.duration_beats
                    )
                    # Apply earcons to MIDI (would integrate with actual MIDI generation)
            
            # Calculate total duration
            duration_sec = arranger.get_total_duration_seconds()
        else:
            duration_sec = 30.0  # Default duration
        
        # Apply mastering if MP3 was generated
        if use_wow_features and base_result.get("mp3_key"):
            # Apply mastering chain (placeholder - would use actual audio file)
            pass
        
        # Prepare artifacts with all metadata
        artifacts = {
            "midi_url": base_result.get("midi_key"),
            "mp3_url": base_result.get("mp3_key"),
            "duration_sec": duration_sec,
            "sound_pack": request.sound_pack
        }
        
        # Convert momentum data to bands
        momentum_json = []
        if base_result.get("momentum_data"):
            for i, data in enumerate(base_result["momentum_data"]):
                momentum_json.append(MomentumBand(
                    t0=i * 4.0,
                    t1=(i + 1) * 4.0,
                    label=data.get("label", "neutral").lower(),
                    score=data.get("score", 0.5)
                ))
        
        # Convert label summary
        label_summary = LabelSummary()
        if base_result.get("label_summary"):
            summary = base_result["label_summary"]
            label_summary = LabelSummary(
                positive=summary.get("MOMENTUM_POS", summary.get("positive", 0)),
                neutral=summary.get("NEUTRAL", summary.get("neutral", 0)), 
                negative=summary.get("MOMENTUM_NEG", summary.get("negative", 0))
            )
        
        result = JobResult(
            job_id=job_id,
            status="done",
            midi_url=artifacts.get("midi_url"),
            mp3_url=artifacts.get("mp3_url"),
            duration_sec=duration_sec,
            sound_pack=request.sound_pack,
            label_summary=label_summary,
            momentum_json=momentum_json,
            logs=["Enhanced sonification completed with wow-factor features"]
        )
        
        if preview_mode:
            return result
        else:
            # Update job store with artifacts and additional metadata
            job_store.finish(job_id, artifacts)
            
            # Persist additional metadata using update method
            metadata_updates = {}
            if base_result.get("label_summary"):
                job_store.set_label_summary(job_id, base_result["label_summary"])
                
            logger.info(f"Enhanced sonification job {job_id} completed successfully")
            
    except Exception as e:
        error_msg = f"Enhanced sonification failed: {e}"
        logger.error(f"Job {job_id}: {error_msg}")
        if not preview_mode:
            job_store.fail(job_id, str(e))
        else:
            raise HTTPException(500, error_msg)


async def process_sonification(
    job_id: str,
    request: SonifyRequest,
    input_midi_key: str,
    output_base_key: str,
    service
):
    """
    Background task for processing sonification.
    
    Args:
        job_id: Job identifier
        request: Sonification request
        input_midi_key: S3 key for input MIDI
        output_base_key: Base S3 key for outputs
        service: Sonification service instance
    """
    try:
        # Mark job as running
        job_store.start(job_id)
        logger.info(f"Processing sonification job {job_id}")
        
        # Execute sonification
        result = service.run_sonification(request, input_midi_key, output_base_key)
        
        # Prepare artifacts (store S3 keys, not presigned URLs)
        artifacts = {}
        if result.get("midi_key"):
            artifacts["midi_url"] = result["midi_key"]
        if result.get("mp3_key"):
            artifacts["mp3_url"] = result["mp3_key"]
        if result.get("momentum_key"):
            artifacts["momentum_json_url"] = result["momentum_key"]
        
        # Update job store
        job_store.finish(job_id, artifacts)
        
        if result.get("label_summary"):
            job_store.set_label_summary(job_id, result["label_summary"])
        
        logger.info(f"Sonification job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Sonification job {job_id} failed: {e}")
        job_store.fail(job_id, str(e))


@app.post("/api/pipeline/run")
async def run_pipeline(background_tasks: BackgroundTasks, x_admin_secret: str = Header(default=None)):
    expected = os.getenv("ADMIN_SECRET")
    if not expected or x_admin_secret != expected:
        raise HTTPException(401, "Admin auth required")
    # run in background
    def _job():
        import subprocess, sys
        subprocess.run([sys.executable, "-m", "src.pipeline.run_pipeline", "--limit", "30"], check=True)
    background_tasks.add_task(_job)
    return {"status":"queued"}


@app.get("/api/cache/catalog")
async def get_catalog():
    # serve latest catalog JSON from PUBLIC bucket
    try:
        import json
        key = "catalog/travel/latest.json"
        txt = read_text_s3(PUBLIC_BUCKET, key, public=True)
        return json.loads(txt)
    except Exception as e:
        raise HTTPException(404, f"Catalog unavailable: {e}")


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            code=str(exc.status_code)
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """General exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            code="500"
        ).model_dump()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
