import pandas as pd
import io
import re
import datetime as dt
from typing import List, Dict, Any

# Required columns for each format (case-insensitive)
REQ_GSC = {"date", "clicks", "impressions", "position"}
REQ_RANK = {"keyword", "url", "position"}

def _detect_format(df: pd.DataFrame, declared: str = "") -> str:
    """Detect CSV format based on columns or declared type."""
    lc = set(df.columns.str.lower())
    
    if declared == "gsc" or REQ_GSC <= lc:
        return "gsc"
    if declared == "rank" or REQ_RANK <= lc:
        return "rank"
    
    raise ValueError("Cannot detect file type. Please specify GSC or Rank format.")

def load_csv(blob: bytes, name: str, declared: str = "") -> List[Dict[str, Any]]:
    """Load and normalize CSV data into common schema."""
    try:
        # Read file based on extension
        if name.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(blob))
        else:
            df = pd.read_csv(io.BytesIO(blob), sep=None, engine="python")
        
        # Memory guard: limit to 50k rows to prevent server overload
        original_rows = len(df)
        if len(df) > 50000:
            df = df.sample(50000, random_state=42)  # Deterministic sampling
            print(f"CSV too large ({original_rows} rows), sampled down to 50,000 rows")
        
        # Normalize column names
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Detect format
        ftype = _detect_format(df, declared)
        rows = []
        
        if ftype == "gsc":
            # Handle GSC format (page or query export)
            for _, r in df.iterrows():
                rows.append({
                    "metric_type": "gsc",
                    "date": r.get("date", dt.date.today()),
                    "keyword": r.get("query", "") or r.get("page", ""),
                    "url": r.get("page", "") or r.get("query", ""),
                    "rank": int(r.get("position", 100)),
                    "clicks": int(r.get("clicks", 0)),
                    "impressions": int(r.get("impressions", 0)),
                    "search_volume": 0  # GSC doesn't provide search volume
                })
        else:
            # Handle Rank file format
            for _, r in df.iterrows():
                rows.append({
                    "metric_type": "rank",
                    "date": dt.date.today(),
                    "keyword": str(r["keyword"]),
                    "url": str(r["url"]),
                    "rank": int(r["position"]),
                    "clicks": 0,  # Rank files don't provide clicks
                    "impressions": 0,  # Rank files don't provide impressions
                    "search_volume": int(r.get("search_volume", 0))
                })
        
        # Add domain extraction for all rows
        for row in rows:
            if row.get("url"):
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(row["url"])
                    row["domain"] = parsed.netloc.lower()
                except:
                    row["domain"] = "unknown"
            else:
                row["domain"] = "unknown"
        
        return rows
        
    except Exception as e:
        raise ValueError(f"Failed to parse CSV: {str(e)}")

def validate_csv_format(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate and return summary of CSV data."""
    if not rows:
        raise ValueError("No data found in CSV")
    
    metric_type = rows[0].get("metric_type", "unknown")
    
    if metric_type == "gsc":
        total_clicks = sum(r.get("clicks", 0) for r in rows)
        total_impressions = sum(r.get("impressions", 0) for r in rows)
        avg_position = sum(r.get("rank", 100) for r in rows) / len(rows)
        
        return {
            "format": "GSC",
            "total_rows": len(rows),
            "total_clicks": total_clicks,
            "total_impressions": total_impressions,
            "avg_position": round(avg_position, 1),
            "date_range": _get_date_range(rows)
        }
    else:
        total_volume = sum(r.get("search_volume", 0) for r in rows)
        avg_position = sum(r.get("rank", 100) for r in rows) / len(rows)
        
        return {
            "format": "Rank File",
            "total_rows": len(rows),
            "total_search_volume": total_volume,
            "avg_position": round(avg_position, 1),
            "date_range": _get_date_range(rows)
        }

def _get_date_range(rows: List[Dict[str, Any]]) -> str:
    """Get date range from CSV data."""
    dates = [r.get("date") for r in rows if r.get("date")]
    if not dates:
        return "No date data"
    
    min_date = min(dates)
    max_date = max(dates)
    
    if min_date == max_date:
        return str(min_date)
    else:
        return f"{min_date} to {max_date}" 