"""
DataForSEO result merger - combines organic, ads, and labs data.
"""

from typing import Dict, List, Any
from datetime import datetime

def merge_dfs(organic: Dict[str, Any], ads: Dict[str, Any], labs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge DataForSEO organic, ads, and labs results."""
    records = []
    
    # Handle organic results
    if not organic or not isinstance(organic, list):
        organic = []
    
    # Handle ads results  
    if not ads or not isinstance(ads, list):
        ads = []
    
    # Handle labs results
    if not labs:
        labs = []
    
    # Process organic results as primary data source
    for org_item in organic:
        if not isinstance(org_item, dict):
            continue
            
        keyword = org_item.get("keyword", "")
        rank = org_item.get("rank_absolute", org_item.get("rank_group", 0))
        
        # Find matching labs data for search volume
        lab_match = next((l for l in labs if l.get("keyword") == keyword), {})
        
        # Find matching ads data
        ad_match = next((a for a in ads 
                        if a.get("keyword") == keyword and 
                           a.get("rank_group") == rank), {})
        
        # Extract rich snippet information
        rich_snippet = org_item.get("rich_snippet", {})
        rich_type = None
        if isinstance(rich_snippet, dict):
            rich_type = rich_snippet.get("type")
        
        # Extract AI overview information
        ai_overview = org_item.get("ai_overview", {})
        ai_present = False
        if isinstance(ai_overview, dict):
            ai_present = ai_overview.get("is_present", False)
        
        # Build record
        record = {
            "keyword": keyword,
            "rank": rank,
            "domain": org_item.get("domain", ""),
            "url": org_item.get("url", ""),
            "title": org_item.get("title", ""),
            "rank_delta": org_item.get("rank_delta", 0),
            "ai_overview": ai_present,
            "rich_snippet_type": rich_type,
            "ads_slot": ad_match.get("ads_position_type") if ad_match else None,
            "search_volume": lab_match.get("monthly_searches", 0) if lab_match else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        records.append(record)
    
    return records

def create_sample_merged_data(keywords: List[str], domain: str = None) -> List[Dict[str, Any]]:
    """Create sample merged data for testing/demo purposes."""
    import random
    
    sample_domains = [
        'google.com', 'youtube.com', 'amazon.com', 'wikipedia.org', 'facebook.com',
        'twitter.com', 'instagram.com', 'linkedin.com', 'reddit.com', 'tiktok.com',
        'github.com', 'stackoverflow.com', 'medium.com', 'quora.com', 'pinterest.com'
    ]
    
    if domain:
        sample_domains.insert(0, domain)
    
    records = []
    for keyword in keywords:
        # Generate 10 sample results per keyword
        for rank in range(1, 11):
            # Higher chance for target domain to appear in top positions
            if domain and rank <= 3 and random.random() > 0.7:
                result_domain = domain
            else:
                result_domain = random.choice(sample_domains)
            
            # Sample rich snippet types
            rich_types = ["video", "shopping_pack", "featured_snippet", "local_pack", None]
            rich_type = random.choice(rich_types) if random.random() < 0.3 else None
            
            # Sample ads positions
            ads_positions = ["top", "bottom", "shopping", None]
            ads_slot = random.choice(ads_positions) if random.random() < 0.2 else None
            
            record = {
                "keyword": keyword,
                "rank": rank,
                "domain": result_domain,
                "url": f"https://{result_domain}/search?q={keyword.replace(' ', '+')}",
                "title": f"{keyword.title()} - {result_domain.title()}",
                "rank_delta": random.randint(-5, 3),
                "ai_overview": random.random() < 0.15 and rank <= 5,
                "rich_snippet_type": rich_type,
                "ads_slot": ads_slot,
                "search_volume": random.randint(100, 50000),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            records.append(record)
    
    return records 