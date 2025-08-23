from fastapi import APIRouter, UploadFile, File, HTTPException
from .session import new_session
from .time_series_ingest import load_period, calculate_deltas
import uuid
import tempfile
import os
import logging
from typing import List

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/upload/timeseries")
async def upload_timeseries(files: List[UploadFile] = File(...)):
    """Upload multiple CSV files for time-series analysis."""
    try:
        if len(files) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 CSV files for time series analysis")
        
        if len(files) > 12:  # Reasonable limit
            raise HTTPException(status_code=400, detail="Maximum 12 periods supported")
        
        periods = []
        temp_files = []
        
        try:
            # Process each uploaded file
            for file in files:
                if not file.filename.endswith('.csv'):
                    raise HTTPException(status_code=400, detail=f"File {file.filename} is not a CSV")
                
                # Create temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp:
                    content = await file.read()
                    tmp.write(content)
                    tmp.flush()
                    temp_files.append(tmp.name)
                    
                    # Extract label from filename (remove extension)
                    label = os.path.splitext(file.filename)[0]
                    
                    # Load and process the period data
                    period_data = load_period(tmp.name, label)
                    periods.append(period_data)
            
            # Sort periods alphabetically by label (or implement date parsing if needed)
            periods.sort(key=lambda p: p["label"])
            
            # Calculate deltas between periods
            periods_with_deltas = calculate_deltas(periods)
            
            # Create session with processed data
            session_id = new_session({
                "type": "timeseries",
                "periods": periods_with_deltas,
                "period_count": len(periods_with_deltas),
                "baseline_period": periods_with_deltas[0]["label"] if periods_with_deltas else None
            })
            
            logger.info(f"Time series session {session_id}: {len(periods_with_deltas)} periods processed")
            
            return {
                "session_id": session_id,
                "periods": len(periods_with_deltas),
                "baseline": periods_with_deltas[0]["label"] if periods_with_deltas else None,
                "summary": {
                    "total_periods": len(periods_with_deltas),
                    "period_labels": [p["label"] for p in periods_with_deltas],
                    "metrics_preview": {
                        "avg_ranks": [round(p["avg_rank"], 2) for p in periods_with_deltas],
                        "click_totals": [p["click_total"] for p in periods_with_deltas],
                        "top3_counts": [p["top3_count"] for p in periods_with_deltas]
                    }
                }
            }
            
        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass
                    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Time series upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Time series processing failed: {str(e)}")

@router.get("/timeseries/{session_id}")
async def get_timeseries_data(session_id: str):
    """Get time series data for a session."""
    from .session import get_session
    
    try:
        session_data = get_session(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session_data.get("type") != "timeseries":
            raise HTTPException(status_code=400, detail="Session is not a time series")
        
        return {
            "session_id": session_id,
            "periods": session_data.get("periods", []),
            "period_count": session_data.get("period_count", 0)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving timeseries {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve time series data") 