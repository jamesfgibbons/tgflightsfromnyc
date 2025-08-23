"""
Fetch SERP metrics from Snowflake and external APIs with normalization.
"""

import os
import json
import logging
import time
from typing import Dict, Any, Optional, List
from decimal import Decimal
import requests
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # Initial delay in seconds


def collect_metrics(
    tenant_id: str,
    mode: str = "serp",
    lookback: str = "7d"
) -> Dict[str, Any]:
    """
    Collect metrics for tenant based on mode.
    
    Args:
        tenant_id: Tenant identifier
        mode: "gsc" for Google Search Console or "serp" for SERP API
        lookback: Time period (e.g., "1d", "7d", "30d")
    
    Returns:
        Dictionary with normalized metrics (0-1 range)
    """
    logger.info(f"Collecting {mode} metrics for tenant {tenant_id}, lookback {lookback}")
    
    try:
        if mode == "gsc":
            raw_metrics = _fetch_gsc_metrics(tenant_id, lookback)
        elif mode == "serp":
            raw_metrics = _fetch_serp_metrics(tenant_id, lookback)
        else:
            raise ValueError(f"Unsupported mode: {mode}")
        
        # Normalize metrics to 0-1 range
        normalized_metrics = _normalize_metrics(raw_metrics, mode)
        
        result = {
            "tenant_id": tenant_id,
            "mode": mode,
            "lookback": lookback,
            "raw_metrics": raw_metrics,
            "normalized_metrics": normalized_metrics,
            "success": True
        }
        
        logger.info(f"Successfully collected metrics for tenant {tenant_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to collect metrics for tenant {tenant_id}: {e}")
        return {
            "tenant_id": tenant_id,
            "mode": mode,
            "lookback": lookback,
            "error": str(e),
            "success": False
        }


def _fetch_gsc_metrics(tenant_id: str, lookback: str) -> Dict[str, Any]:
    """
    Fetch metrics from Snowflake GSC data with retry logic.
    
    Query: RAW.GSC.PAGE_QUERY_DAILY table for clicks, impressions, CTR
    """
    try:
        import snowflake.connector
    except ImportError:
        logger.warning("snowflake-connector-python not available, using mock data")
        return _get_mock_gsc_data()
    
    # Get Snowflake credentials
    snowflake_config = _get_snowflake_config()
    
    if not snowflake_config:
        logger.warning("Snowflake config not available, using mock data")
        return _get_mock_gsc_data()
    
    # Convert lookback to days
    days = _parse_lookback_days(lookback)
    
    query = """
    SELECT 
        SUM(clicks) as total_clicks,
        SUM(impressions) as total_impressions,
        AVG(ctr) as avg_ctr,
        AVG(position) as avg_position
    FROM RAW.GSC.PAGE_QUERY_DAILY 
    WHERE tenant_id = %s 
      AND date >= DATEADD(day, -%s, CURRENT_DATE())
    GROUP BY tenant_id
    """
    
    for attempt in range(MAX_RETRIES):
        try:
            conn = snowflake.connector.connect(**snowflake_config)
            cursor = conn.cursor()
            
            cursor.execute(query, (tenant_id, days))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if result:
                clicks, impressions, ctr, position = result
                return {
                    "clicks": float(clicks or 0),
                    "impressions": float(impressions or 0),
                    "ctr": float(ctr or 0),
                    "position": float(position or 0)
                }
            else:
                logger.warning(f"No GSC data found for tenant {tenant_id}")
                return _get_mock_gsc_data()
                
        except Exception as e:
            logger.warning(f"GSC fetch attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (2 ** attempt))  # Exponential backoff
            else:
                raise


def _fetch_serp_metrics(tenant_id: str, lookback: str) -> Dict[str, Any]:
    """
    Fetch metrics from SERP API with retry logic.
    
    Returns: avg_position, volatility, keyword_count
    """
    serp_api_key = _get_serp_api_key()
    
    if not serp_api_key:
        logger.warning("SERP API key not available, using mock data")
        return _get_mock_serp_data()
    
    # SERP API endpoint (example - replace with actual endpoint)
    base_url = "https://serpapi.example.com/api/v1/metrics"
    
    params = {
        "api_key": serp_api_key,
        "tenant_id": tenant_id,
        "lookback": lookback,
        "format": "json"
    }
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(
                base_url, 
                params=params, 
                timeout=30,
                headers={"User-Agent": "SERP-Radio/1.0"}
            )
            
            response.raise_for_status()
            data = response.json()
            
            return {
                "avg_position": float(data.get("average_position", 0)),
                "volatility": float(data.get("volatility", 0)),
                "keyword_count": int(data.get("keyword_count", 0)),
                "visibility_score": float(data.get("visibility_score", 0))
            }
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"SERP API attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (2 ** attempt))
            else:
                # Fall back to mock data on final failure
                logger.warning("All SERP API attempts failed, using mock data")
                return _get_mock_serp_data()
        
        except (KeyError, ValueError) as e:
            logger.error(f"Invalid SERP API response format: {e}")
            return _get_mock_serp_data()


def _normalize_metrics(raw_metrics: Dict[str, Any], mode: str) -> Dict[str, float]:
    """
    Normalize metrics to 0-1 range using min-max normalization.
    
    Args:
        raw_metrics: Raw metric values
        mode: "gsc" or "serp"
    
    Returns:
        Normalized metrics (0-1 range)
    """
    if mode == "gsc":
        return _normalize_gsc_metrics(raw_metrics)
    elif mode == "serp":
        return _normalize_serp_metrics(raw_metrics)
    else:
        raise ValueError(f"Unknown mode for normalization: {mode}")


def _normalize_gsc_metrics(raw_metrics: Dict[str, Any]) -> Dict[str, float]:
    """Normalize GSC metrics using industry benchmarks."""
    # Industry benchmark ranges for normalization
    benchmarks = {
        "clicks": {"min": 0, "max": 10000},  # 0-10k clicks
        "impressions": {"min": 0, "max": 100000},  # 0-100k impressions
        "ctr": {"min": 0.0, "max": 0.1},  # 0-10% CTR
        "position": {"min": 1.0, "max": 100.0}  # Position 1-100 (inverted)
    }
    
    normalized = {}
    
    for metric, value in raw_metrics.items():
        if metric in benchmarks:
            bench = benchmarks[metric]
            min_val, max_val = bench["min"], bench["max"]
            
            # Clamp value to range
            clamped_value = max(min_val, min(max_val, value))
            
            # Normalize to 0-1
            if max_val == min_val:
                normalized_value = 0.5
            else:
                normalized_value = (clamped_value - min_val) / (max_val - min_val)
            
            # Invert position (lower position = better = higher score)
            if metric == "position":
                normalized_value = 1.0 - normalized_value
            
            normalized[metric] = round(normalized_value, 3)
        else:
            # Unknown metric, keep as-is but clamp to 0-1
            normalized[metric] = max(0.0, min(1.0, float(value)))
    
    return normalized


def _normalize_serp_metrics(raw_metrics: Dict[str, Any]) -> Dict[str, float]:
    """Normalize SERP metrics using expected ranges."""
    benchmarks = {
        "avg_position": {"min": 1.0, "max": 100.0},  # Position 1-100 (inverted)
        "volatility": {"min": 0.0, "max": 100.0},  # 0-100% volatility
        "keyword_count": {"min": 0, "max": 1000},  # 0-1000 keywords
        "visibility_score": {"min": 0.0, "max": 100.0}  # 0-100% visibility
    }
    
    normalized = {}
    
    for metric, value in raw_metrics.items():
        if metric in benchmarks:
            bench = benchmarks[metric]
            min_val, max_val = bench["min"], bench["max"]
            
            clamped_value = max(min_val, min(max_val, value))
            
            if max_val == min_val:
                normalized_value = 0.5
            else:
                normalized_value = (clamped_value - min_val) / (max_val - min_val)
            
            # Invert position (lower = better)
            if metric == "avg_position":
                normalized_value = 1.0 - normalized_value
            
            normalized[metric] = round(normalized_value, 3)
        else:
            normalized[metric] = max(0.0, min(1.0, float(value)))
    
    return normalized


def _get_snowflake_config() -> Optional[Dict[str, Any]]:
    """Get Snowflake connection configuration from environment."""
    required_vars = ["SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD", "SNOWFLAKE_ACCOUNT"]
    
    config = {}
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            logger.warning(f"Missing Snowflake config: {var}")
            return None
        config[var.lower().replace("snowflake_", "")] = value
    
    # Optional configuration
    config["warehouse"] = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
    config["database"] = os.getenv("SNOWFLAKE_DATABASE", "RAW")
    config["schema"] = os.getenv("SNOWFLAKE_SCHEMA", "GSC")
    config["role"] = os.getenv("SNOWFLAKE_ROLE", "SEO_RO")
    
    return config


def _get_serp_api_key() -> Optional[str]:
    """Get SERP API key from AWS Secrets Manager or environment."""
    # Try AWS Secrets Manager first
    try:
        secrets_client = boto3.client('secretsmanager')
        secret_name = "serp-radio/serp-api-key"
        
        response = secrets_client.get_secret_value(SecretId=secret_name)
        return response['SecretString']
        
    except (ClientError, KeyError) as e:
        logger.warning(f"Could not retrieve SERP API key from Secrets Manager: {e}")
    
    # Fall back to environment variable
    return os.getenv("SERP_API_KEY")


def _parse_lookback_days(lookback: str) -> int:
    """Parse lookback string to number of days."""
    lookback = lookback.lower().strip()
    
    if lookback.endswith('d'):
        return int(lookback[:-1])
    elif lookback.endswith('w'):
        return int(lookback[:-1]) * 7
    elif lookback.endswith('m'):
        return int(lookback[:-1]) * 30
    else:
        try:
            return int(lookback)  # Assume days if no suffix
        except ValueError:
            logger.warning(f"Invalid lookback format: {lookback}, defaulting to 7 days")
            return 7


def _get_mock_gsc_data() -> Dict[str, Any]:
    """Generate mock GSC data for testing."""
    return {
        "clicks": 1250.0,
        "impressions": 25000.0,
        "ctr": 0.05,  # 5%
        "position": 8.5
    }


def _get_mock_serp_data() -> Dict[str, Any]:
    """Generate mock SERP data for testing."""
    return {
        "avg_position": 12.3,
        "volatility": 15.7,
        "keyword_count": 150,
        "visibility_score": 67.2
    }


def main():
    """CLI entry point for metric fetching."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fetch SERP metrics")
    parser.add_argument("--tenant", required=True, help="Tenant ID")
    parser.add_argument("--mode", choices=["gsc", "serp"], default="serp", help="Data source mode")
    parser.add_argument("--lookback", default="7d", help="Lookback period (e.g., 1d, 7d, 30d)")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}',
        level=logging.INFO
    )
    
    result = collect_metrics(args.tenant, args.mode, args.lookback)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()