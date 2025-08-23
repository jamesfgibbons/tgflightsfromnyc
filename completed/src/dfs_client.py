"""
Thin DataForSEO client wrapper with authentication.
"""

import os
import asyncio
import aiohttp
import base64
import json
from typing import Dict, List, Any

# DataForSEO API configuration
DFS_BASE_URL = "https://api.dataforseo.com"
DFS_LOGIN = os.getenv("DATAFORSEO_LOGIN")
DFS_PASSWORD = os.getenv("DATAFORSEO_PASSWORD")

def get_auth_header():
    """Generate basic auth header for DataForSEO API."""
    if not DFS_LOGIN or not DFS_PASSWORD:
        raise ValueError("DataForSEO credentials not configured")
    
    credentials = f"{DFS_LOGIN}:{DFS_PASSWORD}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {encoded}"}

async def dfs_post(endpoint: str, data: List[Dict], priority: int = 2) -> Dict[str, Any]:
    """Post task to DataForSEO API."""
    url = f"{DFS_BASE_URL}{endpoint}"
    headers = {
        **get_auth_header(),
        "Content-Type": "application/json"
    }
    
    # Add priority to each task
    for item in data:
        item["priority"] = priority
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as response:
            if response.status != 200:
                raise Exception(f"DataForSEO API error: {response.status}")
            
            result = await response.json()
            if result.get("status_code") != 20000:
                raise Exception(f"DataForSEO task failed: {result.get('status_message')}")
            
            return result

async def dfs_get(task_result: Dict[str, Any]) -> Dict[str, Any]:
    """Get results from DataForSEO task."""
    if not task_result.get("tasks") or not task_result["tasks"]:
        raise Exception("No tasks in DataForSEO response")
    
    task = task_result["tasks"][0]
    if task.get("status_code") != 20000:
        raise Exception(f"DataForSEO task error: {task.get('status_message')}")
    
    # For immediate results, return the task
    if "result" in task:
        return task["result"]
    
    # For queued tasks, we'd need to poll - for now return task info
    return task

async def dfs_batch(keywords: List[str]) -> List[Dict[str, Any]]:
    """Fetch comprehensive SERP data from DataForSEO."""
    if not keywords:
        return []
    
    # Limit keywords to prevent excessive API costs
    max_keywords = int(os.getenv("DFS_MAX_KEYWORDS", "50"))
    keywords = keywords[:max_keywords]
    
    # Prepare task body
    body = [{
        "keyword": kw,
        "location_code": int(os.getenv("DFS_LOCATION", "2840")),
        "language_code": "en",
        "device": os.getenv("DFS_DEVICE", "mobile"),
        "include_serp_info": True,
        "include_ai_overview": True
    } for kw in keywords]
    
    try:
        # Get organic results
        organic_task = await dfs_post("/v3/serp/google/organic/task_post", body, 
                                    priority=int(os.getenv("DFS_PRIORITY", "2")))
        organic = await dfs_get(organic_task)
        
        # Get ads results
        ads_task = await dfs_post("/v3/serp/google/ads_search/task_post", body, priority=2)
        ads = await dfs_get(ads_task)
        
        # Get Labs data for search volume
        labs_body = {
            "keywords": keywords,
            "location_code": int(os.getenv("DFS_LOCATION", "2840")),
            "language_code": "en"
        }
        labs_res = await dfs_post("/v3/dataforseo_labs/google/ranked_keywords/live", [labs_body])
        labs = labs_res["tasks"][0]["result"][0]["items"] if labs_res.get("tasks") else []
        
        # Merge results
        from .merge import merge_dfs
        df_records = merge_dfs(organic, ads, labs)
        
        return df_records
        
    except Exception as e:
        print(f"DataForSEO API error: {e}")
        # Fallback to sample data
        return [] 