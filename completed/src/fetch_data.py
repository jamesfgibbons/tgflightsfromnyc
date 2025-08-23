"""
Data fetching module for SERP Loop Radio.
Handles DataForSEO API calls to collect search ranking data.
"""

import os
import json
import requests
import pandas as pd
from datetime import date, datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataForSEOClient:
    """Client for DataForSEO API interactions."""
    
    def __init__(self, login: str, password: str):
        self.login = login
        self.password = password
        self.base_url = "https://api.dataforseo.com/v3"
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _make_request(self, endpoint: str, data: List[Dict]) -> Dict[str, Any]:
        """Make authenticated request to DataForSEO API with retry logic."""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.post(
                url,
                auth=(self.login, self.password),
                headers={"Content-Type": "application/json"},
                json=data,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
    
    def get_serp_results(self, keyword: str, location_code: int = 2840) -> Dict[str, Any]:
        """Get SERP results for a specific keyword."""
        data = [{
            "keyword": keyword,
            "location_code": location_code,
            "language_code": "en",
            "device": "desktop",
            "os": "windows"
        }]
        
        return self._make_request("serp/google/organic/live/advanced", data)
    
    def get_ranked_keywords(self, target_domain: str, limit: int = 100) -> Dict[str, Any]:
        """Get ranked keywords for a domain."""
        data = [{
            "target": target_domain,
            "location_code": 2840,
            "language_code": "en",
            "limit": limit
        }]
        
        return self._make_request("dataforseo_labs/google/ranked_keywords/live", data)


def collect_serp_data(day: date, keyword_file: Path) -> pd.DataFrame:
    """
    Collect SERP data for all keywords and return unified DataFrame.
    
    Args:
        day: Target date for data collection
        keyword_file: Path to file containing keywords (one per line)
        
    Returns:
        DataFrame with columns: keyword, rank_absolute, rich_type, engine, 
                               domain, share_pct, segment, ai_overview, etv
    """
    # Get credentials from environment
    login = os.getenv("DATAFORSEO_LOGIN")
    password = os.getenv("DATAFORSEO_PASSWORD")
    brand_domain = os.getenv("BRAND_DOMAIN", "mybrand.com")
    
    if not login or not password:
        raise ValueError("DataForSEO credentials not found in environment")
    
    client = DataForSEOClient(login, password)
    
    # Read keywords
    with open(keyword_file, 'r') as f:
        keywords = [line.strip() for line in f if line.strip()]
    
    logger.info(f"Processing {len(keywords)} keywords for {day}")
    
    results = []
    
    for keyword in keywords:
        try:
            logger.info(f"Fetching SERP data for: {keyword}")
            
            # Get SERP results
            serp_response = client.get_serp_results(keyword)
            
            if serp_response.get("status_code") != 20000:
                logger.warning(f"API error for {keyword}: {serp_response.get('status_message')}")
                continue
            
            # Parse SERP results
            for task in serp_response.get("tasks", []):
                for result in task.get("result", []):
                    items = result.get("items", [])
                    
                    # Process organic results
                    for i, item in enumerate(items):
                        if item.get("type") == "organic":
                            domain = extract_domain(item.get("domain", ""))
                            
                            # Determine engine (simplified - assume google_web)
                            engine = "google_web"
                            
                            # Check for AI overview
                            ai_overview = bool(result.get("ai_overview"))
                            
                            # Extract rich snippet type
                            rich_type = ""
                            if item.get("rich_snippet"):
                                rich_type = item.get("rich_snippet", {}).get("type", "")
                            
                            # Estimate traffic value (simplified)
                            etv = item.get("estimated_traffic", 0)
                            
                            # Determine segment (simplified geo mapping)
                            segment = "Central"  # Default, could be enhanced with location data
                            
                            # Calculate share percentage (simplified)
                            share_pct = max(0, (10 - i) / 10) if i < 10 else 0
                            
                            results.append({
                                "date": day,
                                "keyword": keyword,
                                "rank_absolute": i + 1,
                                "rich_type": rich_type,
                                "engine": engine,
                                "domain": domain,
                                "share_pct": share_pct,
                                "segment": segment,
                                "ai_overview": ai_overview,
                                "etv": etv,
                                "brand_rank": i + 1 if domain == brand_domain else None
                            })
            
            # Get competitor analysis
            try:
                ranked_response = client.get_ranked_keywords(brand_domain)
                # Process ranked keywords for additional insights
                # (implementation simplified for MVP)
                
            except Exception as e:
                logger.warning(f"Could not fetch ranked keywords: {e}")
                
        except Exception as e:
            logger.error(f"Error processing keyword {keyword}: {e}")
            continue
    
    df = pd.DataFrame(results)
    logger.info(f"Collected {len(df)} SERP records")
    
    return df


def extract_domain(url: str) -> str:
    """Extract clean domain from URL."""
    if not url:
        return ""
    
    # Remove protocol
    domain = url.replace("https://", "").replace("http://", "")
    
    # Remove www
    if domain.startswith("www."):
        domain = domain[4:]
    
    # Take first part before path
    domain = domain.split("/")[0]
    
    return domain


def get_top_competitors(brand_domain: str, keywords: List[str]) -> List[str]:
    """Get top 3 competitors based on keyword overlap."""
    # Simplified implementation - would need more sophisticated competitor analysis
    # For MVP, return common competitors in the space
    common_competitors = [
        "zendesk.com",
        "intercom.com", 
        "freshworks.com",
        "salesforce.com"
    ]
    
    return common_competitors[:3]


if __name__ == "__main__":
    # Test with sample data
    from datetime import date
    test_keywords = Path("config/keywords.txt")
    
    if test_keywords.exists():
        df = collect_serp_data(date.today(), test_keywords)
        print(f"Collected {len(df)} records")
        print(df.head())
    else:
        print("Keywords file not found. Create config/keywords.txt first.") 