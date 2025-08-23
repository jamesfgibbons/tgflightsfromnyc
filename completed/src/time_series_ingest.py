import pandas as pd
import datetime as dt
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

def load_period(path: str, label: str) -> Dict[str, Any]:
    """Load a CSV file and extract period metrics for sonification."""
    try:
        df = pd.read_csv(path)
        
        # Normalize column names (case-insensitive)
        df.columns = [c.lower().strip() for c in df.columns]
        logger.info(f"Loaded CSV with columns: {list(df.columns)}")
        
        # Map column names to expected fields
        column_mapping = {
            'top queries': 'keyword',
            'clicks': 'clicks', 
            'impressions': 'impr',
            'position': 'rank'
        }
        
        # Apply column mapping
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df[new_name] = df[old_name]
        
        # Ensure required columns exist
        required_cols = ['clicks', 'impr', 'rank']
        for col in required_cols:
            if col not in df.columns:
                logger.error(f"Missing required column: {col}")
                raise ValueError(f"Missing required column: {col}")
        
        # Convert to numeric, handling errors
        df['clicks'] = pd.to_numeric(df['clicks'], errors='coerce').fillna(0)
        df['impr'] = pd.to_numeric(df['impr'], errors='coerce').fillna(0) 
        df['rank'] = pd.to_numeric(df['rank'], errors='coerce').fillna(100)
        
        # Calculate derived metrics
        metrics = {
            "label": label,
            "avg_rank": float(df["rank"].mean()),
            "top3_count": int((df["rank"] <= 3).sum()),
            "click_total": int(df["clicks"].sum()),
            "impr": int(df["impr"].sum()),
            "row_count": len(df)
        }
        
        # Calculate CTR safely
        metrics["ctr"] = float(metrics["click_total"] / metrics["impr"]) if metrics["impr"] > 0 else 0.0
        
        logger.info(f"Period '{label}': {metrics['row_count']} rows, avg_rank={metrics['avg_rank']:.2f}, top3={metrics['top3_count']}, clicks={metrics['click_total']}, CTR={metrics['ctr']:.4f}")
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error loading period {label}: {str(e)}")
        raise

def calculate_deltas(periods: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculate period-over-period deltas for sonification."""
    if len(periods) < 2:
        return periods
    
    enhanced_periods = []
    baseline = periods[0]
    
    for i, period in enumerate(periods):
        enhanced = period.copy()
        
        if i > 0:
            prev_period = periods[i-1]
            enhanced.update({
                "delta_clicks": period["click_total"] - prev_period["click_total"],
                "delta_top3": period["top3_count"] - prev_period["top3_count"],
                "delta_ctr": period["ctr"] - prev_period["ctr"],
                "delta_rank": period["avg_rank"] - prev_period["avg_rank"]
            })
        else:
            # First period has no deltas
            enhanced.update({
                "delta_clicks": 0,
                "delta_top3": 0, 
                "delta_ctr": 0.0,
                "delta_rank": 0.0
            })
        
        enhanced_periods.append(enhanced)
    
    return enhanced_periods 