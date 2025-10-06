"""
FastAPI application for SERP Radio production backend.
"""

import csv
import io
import logging
import os
import pathlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import pandas as pd
from fastapi import FastAPI, BackgroundTasks, HTTPException, UploadFile, File, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse

from .models import (
    SonifyRequest, SonifyResponse, JobStatus, UploadCsvResponse, 
    HealthResponse, ErrorResponse, ShareResponse
)
from .api_models import (
    JobResult, LabelSummary, MomentumBand, HeroStatusResponse,
    HeroStatusPack, HealthResponse as ApiHealthResponse,
    PromptIntakeRequest, PromptBatchIntakeRequest, PromptIntakeResponse,
    AdhocRunRequest, AdhocRunResponse, VibeNetRunList, VibeNetRun,
    VibeNetItemList, VibeNetItem,
)
from .soundpacks import get_sound_pack, list_sound_packs, DEFAULT_PACK
from .arranger import MusicArranger
from .earcons import create_earcon_generator
from .mixing import master_audio_file
from .storage import put_bytes, get_presigned_url, ensure_tenant_prefix, write_json, S3Storage, StorageError, read_text_s3
from .jobstore import job_store
from .rules_api import router as rules_router
from .vibe_api import router as vibe_router
from .board_api import router as board_router
from .vibenet_api import router as vibenet_router
from .v5_aliases import router as v5_alias_router
from .book_api import router as book_router
from .aliases import alias_router
from .llm_pipeline import run_daily_xai
from .llm_xai import call_xai_with_cache
from .web_search_api import router as web_router
from .travel_context_api import router as travel_router
from .notify_api import router as notify_router
from .db import supabase_select, supabase_insert, list_vibenet_runs, list_vibenet_items
from .pipeline.openai_client import FlightLLM
from .pipeline.schemas import LLMFlightResult, MomentumBand as PipelineMomentumBand
from .pipeline import travel_pipeline
from .pipeline.nostalgia import brand_to_sound_pack, routing_to_energy

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
# CORS configuration (env override supported)
_cors_env = os.getenv("CORS_ORIGINS")
if _cors_env:
    CORS_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()]
else:
    CORS_ORIGINS = [
        "https://serpradio.lovable.app",
        "https://serpradio.com",
        "https://www.serpradio.com",
        "https://lovable.dev",
        "https://app.lovable.dev",
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
app.include_router(board_router)
app.include_router(v5_alias_router)
app.include_router(web_router)
app.include_router(travel_router)
app.include_router(book_router)
app.include_router(alias_router)
app.include_router(notify_router)

# ---- Aggregations / summaries ----

@app.get("/api/llm/run_summary")
async def llm_run_summary(run_id: str):
    """Aggregate metrics for a given run_id from llm_results.

    Returns counts by provider/model/status and basic timing stats.
    """
    try:
        from .storage import get_supabase_client, get_storage_backend
        if get_storage_backend() != "supabase":
            raise HTTPException(503, "Supabase not configured")
        sb = get_supabase_client()
        q = sb.table("llm_results").select("provider,model,status,latency_ms").eq("run_id", run_id).limit(2000)
        data = getattr(q.execute(), "data", []) or []
        by: dict[str, dict[str, int]] = {}
        total = 0
        latencies: list[int] = []
        for r in data:
            total += 1
            prov = (r.get("provider") or "").lower() or "unknown"
            by.setdefault(prov, {})
            model = r.get("model") or "unknown"
            key = f"{model}:{r.get('status') or 'completed'}"
            by[prov][key] = by[prov].get(key, 0) + 1
            try:
                lat = int(r.get("latency_ms") or 0)
                if lat > 0:
                    latencies.append(lat)
            except Exception:
                pass
        latencies.sort()
        def pct(p: float) -> int:
            if not latencies:
                return 0
            i = max(0, min(len(latencies)-1, int(p * (len(latencies)-1))))
            return int(latencies[i])
        stats = {
            "count": total,
            "p50_ms": pct(0.50),
            "p90_ms": pct(0.90),
            "p99_ms": pct(0.99),
        }
        return {"run_id": run_id, "by": by, "stats": stats}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(404, f"run_summary unavailable: {e}")

# Dependencies
def get_sonification_service():
    """Dependency injection for sonification service.

    Imported lazily to avoid optional audio deps blocking non-audio endpoints.
    """
    try:
        from .sonify_service import create_sonification_service  # type: ignore
        return create_sonification_service(STORAGE_BUCKET)
    except Exception as e:
        raise HTTPException(503, f"Sonify service unavailable: {e}")


def _model_from_dict(model_cls, data: dict):
    try:
        return model_cls.model_validate(data)
    except Exception:
        filtered = {k: data.get(k) for k in model_cls.model_fields}
        return model_cls(**filtered)


def _persist_vibenet_run(run_payload: dict[str, Any], item_payload: dict[str, Any] | None) -> Optional[str]:
    run_id: Optional[str] = None
    try:
        rows = supabase_insert("vibenet_runs", run_payload) or []
        if rows:
            first = rows[0] if isinstance(rows, list) else rows
            run_id = first.get("id") if isinstance(first, dict) else None
            if run_id and item_payload:
                payload = dict(item_payload)
                payload["run_id"] = run_id
                supabase_insert("vibenet_items", payload)
    except Exception as exc:  # best-effort only
        logger.warning(f"persist_vibenet_run failed: {exc}")
    return run_id


# ---- Prompt Intake (Feeder) ----

INTAKE_TOKEN = os.getenv("INTAKE_TOKEN")  # Optional shared secret for intake endpoints


def _require_intake_auth(x_client_token: str | None):
    if INTAKE_TOKEN and x_client_token != INTAKE_TOKEN:
        raise HTTPException(401, "Invalid intake token")


@app.post("/api/intake/prompt", response_model=PromptIntakeResponse)
async def intake_prompt(req: PromptIntakeRequest, x_client_token: str | None = Header(default=None)):
    _require_intake_auth(x_client_token)
    # Best-effort Supabase insert
    try:
        from .storage import get_storage_backend, get_supabase_client
        request_id = str(uuid.uuid4())
        if get_storage_backend() == "supabase":
            sb = get_supabase_client()
            record = {
                "id": request_id,
                "source": req.source,
                "prompt_metadata": req.metadata or {},
                "request_payload": {"prompt": req.prompt, "config": req.config or {}},
                "status": "accepted",
            }
            sb.table("api_results").insert(record).execute()
        return PromptIntakeResponse(request_id=request_id, status="accepted")
    except Exception as e:
        # Still accept to keep feeder decoupled; logging for server visibility
        logger.warning(f"intake_prompt: supabase insert failed: {e}")
        return PromptIntakeResponse(request_id=str(uuid.uuid4()), status="accepted")


@app.post("/api/intake/prompts")
async def intake_prompts(req: PromptBatchIntakeRequest, x_client_token: str | None = Header(default=None)):
    _require_intake_auth(x_client_token)
    accepted = []
    try:
        from .storage import get_storage_backend, get_supabase_client
        is_sb = get_storage_backend() == "supabase"
        sb = get_supabase_client() if is_sb else None
        rows = []
        for item in req.items:
            rid = str(uuid.uuid4())
            accepted.append(rid)
            rows.append({
                "id": rid,
                "source": item.source,
                "prompt_metadata": item.metadata or {},
                "request_payload": {"prompt": item.prompt, "config": item.config or {}},
                "status": "accepted",
            })
        if sb and rows:
            for i in range(0, len(rows), 500):
                sb.table("api_results").insert(rows[i:i+500]).execute()
    except Exception as e:
        logger.warning(f"intake_prompts: supabase insert failed: {e}")
    return {"ok": True, "accepted": len(accepted), "request_ids": accepted}


@app.post("/api/adhoc/run", response_model=AdhocRunResponse)
async def adhoc_run(req: AdhocRunRequest, x_admin_secret: str | None = Header(default=None)):
    expected = os.getenv("ADMIN_SECRET")
    if expected and x_admin_secret != expected:
        raise HTTPException(401, "Admin auth required")

    try:
        llm = FlightLLM()
    except Exception as e:
        raise HTTPException(503, f"LLM provider unavailable: {e}")

    try:
        llm_raw = llm.analyze_prompt(req.prompt)
    except Exception as e:
        raise HTTPException(502, f"Prompt analysis failed: {e}")

    flight_kwargs = {
        key: llm_raw.get(key)
        for key in (
            "estimated_price_range",
            "best_booking_window",
            "peak_discount_times",
            "carrier_likelihood",
            "routing_strategy",
            "novelty_score",
            "sonification_params",
        )
        if llm_raw.get(key) is not None
    }

    origin = req.origin or llm_raw.get("origin") or "NYC"
    destination = req.destination or llm_raw.get("destination") or "LAS"

    llm_result = LLMFlightResult(
        origin=origin,
        destination=destination,
        prompt=req.prompt,
        **flight_kwargs,
    )

    bands: list[PipelineMomentumBand] = travel_pipeline._bands_from_llm(llm_result)
    summary_counts = travel_pipeline._label_summary(bands)

    brand_hint = None
    if llm_result.carrier_likelihood:
        brand_hint = llm_result.carrier_likelihood[0]
    brand_hint = brand_hint or destination or "Unknown"
    sound_pack = req.sound_pack or brand_to_sound_pack(str(brand_hint))
    tempo, bars = routing_to_energy(llm_result.routing_strategy or "direct")

    service = get_sonification_service()

    job_id = job_store.create()
    job_store.start(job_id)
    output_base = ensure_tenant_prefix("adhoc", "runs", job_id)

    momentum_payload = [band.model_dump() for band in bands]
    override_metrics = {
        "momentum_data": momentum_payload,
        "ctr": 0.62,
        "impressions": 0.58,
        "position": 0.52,
        "clicks": 0.6,
    }

    sreq = SonifyRequest(
        tenant="adhoc",
        source="demo",
        total_bars=bars,
        tempo_base=tempo,
        sound_pack=sound_pack,
        override_metrics=override_metrics,
    )

    base = service.run_sonification(sreq, None, output_base)

    midi_key = base.get("midi_key")
    mp3_key = base.get("mp3_key")
    midi_url = get_presigned_url(service.s3_bucket, midi_key) if midi_key else None
    mp3_url = get_presigned_url(service.s3_bucket, mp3_key) if mp3_key else None

    counts = {
        "positive": summary_counts.get("positive", 0),
        "neutral": summary_counts.get("neutral", 0),
        "negative": summary_counts.get("negative", 0),
    }

    api_bands = [MomentumBand(**band.model_dump()) for band in bands]
    job = JobResult(
        job_id=job_id,
        status="done",
        midi_url=midi_url,
        mp3_url=mp3_url,
        duration_sec=base.get("duration_sec", float(bars) * 60.0 / max(tempo, 1)),
        sound_pack=sound_pack,
        label_summary=LabelSummary(**counts),
        momentum_json=api_bands,
        logs=[f"sound_pack={sound_pack}", f"tempo={tempo}", f"bars={bars}"],
    )

    job_store.finish(
        job_id,
        {
            "midi_url": midi_key,
            "mp3_url": mp3_key,
            "duration_sec": job.duration_sec,
            "sound_pack": sound_pack,
        },
    )

    run_payload = {
        "channel": req.channel,
        "theme": req.theme,
        "sub_theme": req.sub_theme,
        "generated": datetime.utcnow().isoformat(),
        "total": 1,
        "notes": "adhoc",
    }
    item_payload = {
        "entry_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "channel": req.channel,
        "theme": req.theme,
        "sub_theme": req.sub_theme,
        "origin": origin,
        "destination": destination,
        "brand": brand_hint,
        "title": f"{origin}->{destination}",
        "prompt": req.prompt,
        "sound_pack": sound_pack,
        "duration_sec": job.duration_sec,
        "mp3_url": mp3_url,
        "midi_url": midi_url,
        "momentum_json": momentum_payload,
        "label_summary": counts,
    }

    run_id = _persist_vibenet_run(run_payload, item_payload)

    analysis = {
        "llm_result": llm_raw,
        "sound_pack": sound_pack,
        "tempo": tempo,
        "total_bars": bars,
        "run_id": run_id,
    }

    return AdhocRunResponse(run_id=run_id, job=job, analysis=analysis)
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


@app.post("/api/llm/run")
async def run_llm_daily(background_tasks: BackgroundTasks, limit: int = 50, model: str | None = None, x_admin_secret: str = Header(default=None)):
    expected = os.getenv("ADMIN_SECRET")
    if not expected or x_admin_secret != expected:
        raise HTTPException(401, "Admin auth required")

    def _job():
        try:
            run_daily_xai(max_items=limit, model=model)
        except Exception as e:
            logger.error(f"LLM daily pipeline failed: {e}")

    background_tasks.add_task(_job)
    return {"status": "queued", "limit": limit, "model": model or os.getenv("GROK_MODEL", "grok-beta")}


@app.get("/api/cache/catalog")
async def get_catalog(theme: str | None = None):
    # serve latest catalog JSON from PUBLIC bucket
    try:
        import json
        keys = []
        if theme:
            keys.append(f"catalog/travel/{theme}/latest.json")
        keys.append("catalog/travel/latest.json")

        last_error: Exception | None = None
        for key in keys:
            try:
                txt = read_text_s3(PUBLIC_BUCKET, key, public=True)
                payload = json.loads(txt)
                payload.setdefault("source", key)
                return payload
            except Exception as inner_error:  # try fallback
                last_error = inner_error
                continue

        raise last_error if last_error else RuntimeError("catalog not found")
    except Exception as e:
        raise HTTPException(404, f"Catalog unavailable: {e}")


@app.post("/api/vibenet/run")
async def vibenet_run(background_tasks: BackgroundTasks,
                      vertical: str = "travel",
                      theme: str = "flights_from_nyc",
                      sub_themes: list[str] | None = None,
                      tracks_per_theme: int = 6,
                      limit: int = 24,
                      x_admin_secret: str = Header(default=None)):
    expected = os.getenv("ADMIN_SECRET")
    if not expected or x_admin_secret != expected:
        raise HTTPException(401, "Admin auth required")

    def _job():
        import subprocess, sys, json
        args = [sys.executable, "-m", "src.pipeline.run_pipeline",
                "--vertical", vertical,
                "--theme", theme,
                "--tracks-per-theme", str(tracks_per_theme),
                "--limit", str(limit)]
        if sub_themes:
            args.extend(["--sub-themes", *sub_themes])
        subprocess.run(args, check=True)

    background_tasks.add_task(_job)
    return {"status": "queued", "vertical": vertical, "theme": theme, "sub_themes": sub_themes or []}


@app.post("/api/vibenet/run_ski")
async def vibenet_run_ski(background_tasks: BackgroundTasks,
                          limit: int = 100,
                          x_admin_secret: str = Header(default=None)):
    expected = os.getenv("ADMIN_SECRET")
    if not expected or x_admin_secret != expected:
        raise HTTPException(401, "Admin auth required")

    def _job():
        import subprocess, sys
        subprocess.run([sys.executable, "scripts/run_ski_pipeline.py", "--limit", str(limit)], check=True)

    background_tasks.add_task(_job)
    return {"status": "queued", "theme": "ski_season", "limit": limit}


@app.get("/admin/vibenet", response_class=HTMLResponse)
async def admin_vibenet_console():
    html = """
    <!doctype html>
    <html>
    <head>
      <meta charset=\"utf-8\" />
      <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
      <title>VibeNet Console</title>
      <style>
        body {{ font-family: ui-sans-serif, system-ui, -apple-system; max-width: 860px; margin: 24px auto; padding: 0 12px; }}
        fieldset {{ border: 1px solid #ddd; margin-bottom: 16px; }}
        label {{ display:block; margin: 8px 0; }}
        input, select, textarea {{ width: 100%; padding: 6px; }}
        button {{ padding: 8px 12px; }}
        pre {{ background:#f7f7f7; padding:8px; overflow:auto; }}
      </style>
    </head>
    <body>
      <h1>VibeNet Console</h1>

      <fieldset>
        <legend>Run General Pipeline</legend>
        <label>Admin Secret <input id="adm" type="password" placeholder="ADMIN_SECRET" /></label>
        <label>Vertical <input id="vertical" value="travel" /></label>
        <label>Theme <input id="theme" value="flights_from_nyc" /></label>
        <label>Sub-Themes (space separated) <input id="subs" value="non_brand_seo best_time_to_book hidden_city_hacks weekend_getaways" /></label>
        <label>Tracks per Theme <input id="tpt" type="number" value="6" /></label>
        <label>Limit <input id="limit" type="number" value="24" /></label>
        <button onclick="runGeneral()">Queue Run</button>
      </fieldset>

      <fieldset>
        <legend>Run Ski Season (Top 100)</legend>
        <label>Admin Secret <input id="adm2" type="password" placeholder="ADMIN_SECRET" /></label>
        <label>Limit <input id="limit2" type="number" value="100" /></label>
        <button onclick="runSki()">Queue Ski Run</button>
      </fieldset>

      <fieldset>
        <legend>Results</legend>
        <pre id="out">Ready.</pre>
      </fieldset>

      <script>
        async function runGeneral() {{
          const adm = document.getElementById('adm').value;
          const vertical = document.getElementById('vertical').value;
          const theme = document.getElementById('theme').value;
          const subs = document.getElementById('subs').value.trim().split(/\s+/).filter(Boolean);
          const tpt = parseInt(document.getElementById('tpt').value||'6');
          const limit = parseInt(document.getElementById('limit').value||'24');
          const res = await fetch('/api/vibenet/run?vertical='+encodeURIComponent(vertical)+'&theme='+encodeURIComponent(theme)+'&tracks_per_theme='+tpt+'&limit='+limit+(subs.length?('&'+subs.map(s=>'sub_themes='+encodeURIComponent(s)).join('&')):''), {{
            method: 'POST', headers: {{ 'X-Admin-Secret': adm }}
          }});
          document.getElementById('out').textContent = JSON.stringify(await res.json(), null, 2);
        }}
        async function runSki() {{
          const adm = document.getElementById('adm2').value;
          const limit = parseInt(document.getElementById('limit2').value||'100');
          const res = await fetch('/api/vibenet/run_ski?limit='+limit, {{ method:'POST', headers: {{ 'X-Admin-Secret': adm }} }});
          document.getElementById('out').textContent = JSON.stringify(await res.json(), null, 2);
        }}
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.get("/api/vibenet/runs", response_model=VibeNetRunList)
async def vibenet_runs(limit: int = 50, theme: str | None = None, channel: str | None = None):
    rows = list_vibenet_runs(limit=limit, theme=theme, channel=channel)
    if rows is None:
        return VibeNetRunList(items=[], source="none")
    items = [_model_from_dict(VibeNetRun, row) for row in rows]
    return VibeNetRunList(items=items, source="supabase")


@app.get("/api/vibenet/items", response_model=VibeNetItemList)
async def vibenet_run_items(run_id: str, limit: int = 200):
    rows = list_vibenet_items(run_id, limit=limit)
    if rows is None:
        return VibeNetItemList(items=[], source="none")
    items = [_model_from_dict(VibeNetItem, row) for row in rows]
    return VibeNetItemList(items=items, source="supabase")


@app.get("/api/travel/subthemes")
async def travel_subthemes():
    try:
        import json
        key = "catalog/travel/latest.json"
        txt = read_text_s3(PUBLIC_BUCKET, key, public=True)
        data = json.loads(txt)
        items = data.get("items", [])
        subs = {}
        for it in items:
            st = (it.get("sub_theme") or "").strip()
            if not st:
                continue
            subs[st] = subs.get(st, 0) + 1
        return {"total": sum(subs.values()), "subthemes": sorted([{ "name": k, "count": v } for k,v in subs.items()], key=lambda x: (-x["count"], x["name"]))}
    except Exception as e:
        raise HTTPException(404, f"Subthemes unavailable: {e}")


@app.get("/api/travel/catalog")
async def travel_catalog(sub_theme: str | None = None, origin: str | None = None, destination: str | None = None, brand: str | None = None, limit: int = 100, theme: str | None = None):
    try:
        import json
        keys = []
        if theme:
            keys.append(f"catalog/travel/{theme}/latest.json")
        keys.append("catalog/travel/latest.json")

        txt = None
        last_error: Exception | None = None
        for key in keys:
            try:
                txt = read_text_s3(PUBLIC_BUCKET, key, public=True)
                break
            except Exception as inner_error:
                last_error = inner_error
                continue

        if txt is None:
            raise last_error if last_error else RuntimeError("catalog not found")
        data = json.loads(txt)
        items = data.get("items", [])

        def _match(it: dict) -> bool:
            if sub_theme and (it.get("sub_theme") or "").lower() != sub_theme.lower():
                return False
            if origin and (it.get("origin") or "").upper() != origin.upper():
                return False
            if destination and (it.get("destination") or "").upper() != destination.upper():
                return False
            if brand and (it.get("brand") or "").lower() != brand.lower():
                return False
            return True

        out = [it for it in items if _match(it)]
        if limit and limit > 0:
            out = out[:limit]
        return {"generated": data.get("generated"), "total": len(out), "items": out}
    except Exception as e:
        raise HTTPException(404, f"Catalog unavailable: {e}")


@app.get("/api/travel/routes_nyc")
async def travel_routes_nyc(origin: str | None = None, limit: int = 5000):
    """Fetch top routes from Supabase table `travel_routes_nyc`.

    - Optional filter by origin (JFK|LGA|EWR)
    - Returns up to `limit` rows ordered by insertion order (assumed pre-sorted by popularity)
    """
    try:
        rows = supabase_select("travel_routes_nyc", limit=limit) or []
        if origin:
            o = origin.upper()
            rows = [r for r in rows if (r.get("origin") or "").upper() == o]
        if limit and limit > 0:
            rows = rows[:limit]
        return {"total": len(rows), "items": rows}
    except Exception as e:
        raise HTTPException(404, f"Routes unavailable: {e}")


@app.get("/api/travel/price_quotes")
async def travel_price_quotes(origin: str | None = None, destination: str | None = None, limit: int = 100):
    """Fetch parsed price quotes from Supabase (table: price_quotes)."""
    try:
        rows = supabase_select("price_quotes", limit=limit) or []
        def _match(it: dict) -> bool:
            if origin and (it.get("origin") or "").upper() != origin.upper():
                return False
            if destination and (it.get("destination") or "").upper() != destination.upper():
                return False
            return True
        out = [r for r in rows if _match(r)]
        return {"total": len(out), "items": out}
    except Exception as e:
        raise HTTPException(404, f"Price quotes unavailable: {e}")


@app.get("/api/travel/price_quotes_latest")
async def travel_price_quotes_latest(origin: str | None = None, destination: str | None = None, limit: int = 100):
    """Fetch latest price quotes per route from view `vw_latest_price_quotes` if present.

    Falls back to `price_quotes` table if the view is missing.
    """
    try:
        from .storage import get_supabase_client, get_storage_backend
        if get_storage_backend() != "supabase":
            raise HTTPException(503, "Supabase not configured")
        sb = get_supabase_client()
        # Try the view first
        try:
            q = sb.table("vw_latest_price_quotes").select("*")
            if origin:
                q = q.eq("origin", origin.upper())
            if destination:
                q = q.eq("destination", destination.upper())
            if limit and limit > 0:
                q = q.limit(limit)
            data = getattr(q.execute(), "data", []) or []
            return {"total": len(data), "items": data}
        except Exception:
            # Fallback to base table
            q = sb.table("price_quotes").select("*")
            if origin:
                q = q.eq("origin", origin.upper())
            if destination:
                q = q.eq("destination", destination.upper())
            if limit and limit > 0:
                q = q.limit(limit)
            data = getattr(q.execute(), "data", []) or []
            return {"total": len(data), "items": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(404, f"Latest quotes unavailable: {e}")


@app.get("/api/travel/cheapest_route")
async def travel_cheapest_route(
    origin: str = "JFK",
    destination_group: str = "LON",  # London area
    window_days: int = 45,
    one_way: bool = True,
    n_results: int = 3,
):
    """Canonical route query using xAI (Grok) with file cache and Supabase logging.

    Note: This uses the LLM to aggregate current pricing info and is best-effort.
    Ensure GROK_API_KEY/XAI_API_KEY is set. Returns raw LLM payload for transparency.
    """
    if destination_group.upper() in ("LON", "LONDON"):
        dests = ["LHR", "LGW", "LCY", "STN", "LTN"]
        dest_label = "London (LHR, LGW, LCY, STN, LTN)"
    else:
        # Accept a comma-separated list in destination_group for custom sets
        dests = [x.strip().upper() for x in destination_group.split(",") if x.strip()]
        dest_label = ", ".join(dests)

    system = (
        "You are an airline fare analyst. Identify truly cheapest all-in prices "
        "(including mandatory fees) from trusted sources. Return STRICT JSON only."
    )
    prompt = (
        f"Find the cheapest {'one-way' if one_way else 'round-trip'} flight from {origin} "
        f"to {dest_label} in the next {window_days} days. "
        f"Include basic fare rules, bag policy, and cite sources with URLs and timestamps.\n\n"
        "Return JSON with: {\n"
        "  \"origin\": string, \"destinations\": [string], \"window_days\": number,\n"
        "  \"cheapest\": { \"price_total\": number, \"currency\": string, \"airline\": string, \"cabin\": string, \"depart_date\": string, \"arrive_airport\": string, \"routing\": [string], \"bags\": string, \"fare_rules\": string, \"source_url\": string, \"checked_at\": string },\n"
        f"  \"alternatives\": [max {n_results-1} items with the same shape]\n"
        "}\n"
        "If data conflicts, prefer airline direct fares over OTAs."
    )
    meta = {"origin": origin, "destinations": dests, "window_days": window_days, "one_way": one_way}
    rec = call_xai_with_cache(prompt, system=system, metadata=meta)
    return rec



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

# ---- Admin: Prompt Library Browser/Editor ----
PROMPT_ROOT = pathlib.Path(__file__).parent / "pipeline" / "prompt_library"

def _safe_join_prompt_path(rel: str) -> pathlib.Path:
    p = (PROMPT_ROOT / rel).resolve()
    if PROMPT_ROOT not in p.parents and p != PROMPT_ROOT:
        raise HTTPException(400, "Invalid path")
    return p


@app.get("/api/admin/prompts/list")
async def admin_prompts_list():
    """List YAML prompt files under the prompt_library tree."""
    items = []
    for path in PROMPT_ROOT.rglob("*.yaml"):
        rel = path.relative_to(PROMPT_ROOT).as_posix()
        items.append(rel)
    items.sort()
    return {"root": PROMPT_ROOT.as_posix(), "count": len(items), "items": items}


@app.get("/api/admin/prompts/get")
async def admin_prompts_get(path: str):
    """Fetch a YAML prompt file content."""
    f = _safe_join_prompt_path(path)
    if not f.exists() or not f.is_file():
        raise HTTPException(404, "File not found")
    return {"path": path, "content": f.read_text(encoding="utf-8")}


@app.put("/api/admin/prompts/save")
async def admin_prompts_save(path: str, content: str, x_admin_secret: str = Header(default=None)):
    expected = os.getenv("ADMIN_SECRET")
    if not expected or x_admin_secret != expected:
        raise HTTPException(401, "Admin auth required")
    f = _safe_join_prompt_path(path)
    # Validate YAML parses
    try:
        yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise HTTPException(400, f"Invalid YAML: {e}")
    # Ensure parent exists
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(content, encoding="utf-8")
    return {"ok": True, "path": path}


@app.get("/admin/prompts", response_class=HTMLResponse)
async def admin_prompts_console():
    html = """
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Prompt Library Editor</title>
      <style>
        body {{ font-family: ui-sans-serif, system-ui, -apple-system; max-width: 980px; margin: 24px auto; padding: 0 12px; }}
        .row {{ display:flex; gap:16px; }}
        .col {{ flex:1; min-width: 0; }}
        textarea {{ width:100%; height: 60vh; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; }}
        select, input {{ width:100%; padding:6px; }}
        button {{ padding: 8px 12px; margin-top: 8px; }}
        pre {{ background:#f7f7f7; padding:8px; overflow:auto; }}
      </style>
    </head>
    <body>
      <h1>Prompt Library Editor</h1>
      <div class="row">
        <div class="col">
          <h3>Files</h3>
          <select id="files" size="20"></select>
          <button onclick="reloadList()">Reload</button>
        </div>
        <div class="col">
          <h3>Editor</h3>
          <label>Admin Secret <input id="adm" type="password" placeholder="ADMIN_SECRET" /></label>
          <textarea id="content"></textarea>
          <button onclick="saveFile()">Save</button>
          <pre id="out">Ready.</pre>
        </div>
      </div>
      <script>
        async function reloadList() {
          const res = await fetch('/api/admin/prompts/list');
          const j = await res.json();
          const sel = document.getElementById('files');
          sel.innerHTML = '';
          j.items.forEach(p=> {
            const opt = document.createElement('option');
            opt.textContent = p; opt.value = p; sel.appendChild(opt);
          });
        }
        async function loadFile() {
          const sel = document.getElementById('files');
          const path = sel.value; if(!path) return;
          const res = await fetch('/api/admin/prompts/get?path='+encodeURIComponent(path));
          const j = await res.json();
          document.getElementById('content').value = j.content || '';
          document.getElementById('out').textContent = 'Loaded: '+path;
        }
        async function saveFile() {
          const sel = document.getElementById('files');
          const path = sel.value; if(!path) return alert('Select a file');
          const adm = document.getElementById('adm').value;
          const content = document.getElementById('content').value;
          const form = new FormData();
          form.append('path', path);
          form.append('content', content);
          const res = await fetch('/api/admin/prompts/save', { method:'PUT', headers: { 'X-Admin-Secret': adm }, body: form });
          document.getElementById('out').textContent = JSON.stringify(await res.json(), null, 2);
        }
        document.getElementById('files').addEventListener('change', loadFile);
        reloadList();
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
