"""
Scorecard aggregator for domain league analysis.
"""

from collections import Counter, defaultdict
from typing import List, Dict, Any

def domain_league(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analyze top-10 unique domains across all keywords.
    Returns domain share analysis for scorecard overture.
    """
    # Filter to top-10 results only
    top10 = [r for r in rows if r.get("rank", 0) <= 10]
    
    if not top10:
        return []
    
    # Count domain appearances
    domain_counter = Counter(r.get("domain", "") for r in top10)
    total_appearances = len(top10)
    
    # Calculate share percentages
    league_table = []
    for domain, count in domain_counter.most_common():
        if domain:  # Skip empty domains
            share = count / total_appearances
            league_table.append({
                "domain": domain,
                "appearances": count,
                "share": share,
                "percentage": round(share * 100, 1)
            })
    
    return league_table

def keyword_performance(rows: List[Dict[str, Any]], target_domain: str = None) -> Dict[str, Any]:
    """
    Analyze keyword performance metrics.
    """
    if not rows:
        return {}
    
    total_keywords = len(set(r.get("keyword", "") for r in rows))
    total_results = len(rows)
    
    # AI Overview analysis
    ai_overview_count = sum(1 for r in rows if r.get("ai_overview", False))
    
    # Rich snippet analysis
    rich_snippets = Counter(r.get("rich_snippet_type") for r in rows if r.get("rich_snippet_type"))
    
    # Ads analysis
    ads_slots = Counter(r.get("ads_slot") for r in rows if r.get("ads_slot"))
    
    # Target domain analysis (if specified)
    target_analysis = {}
    if target_domain:
        target_results = [r for r in rows if r.get("domain") == target_domain]
        if target_results:
            target_ranks = [r.get("rank", 0) for r in target_results]
            target_analysis = {
                "appearances": len(target_results),
                "avg_rank": sum(target_ranks) / len(target_ranks),
                "top3_count": sum(1 for rank in target_ranks if rank <= 3),
                "top10_count": sum(1 for rank in target_ranks if rank <= 10)
            }
    
    return {
        "total_keywords": total_keywords,
        "total_results": total_results,
        "ai_overview_count": ai_overview_count,
        "ai_overview_percentage": round((ai_overview_count / total_results) * 100, 1) if total_results > 0 else 0,
        "rich_snippets": dict(rich_snippets),
        "ads_slots": dict(ads_slots),
        "target_domain_analysis": target_analysis
    }

def generate_recap_insights(rows: List[Dict[str, Any]], target_domain: str = None) -> List[str]:
    """
    Generate human-readable insights for the recap.
    """
    insights = []
    
    if not rows:
        return ["No data available for analysis."]
    
    # Domain league analysis
    league = domain_league(rows)
    if league:
        winner = league[0]
        insights.append(f"🏆 {winner['domain']} dominates with {winner['percentage']}% share")
        
        if len(league) > 1:
            runner_up = league[1]
            insights.append(f"🥈 {runner_up['domain']} follows with {runner_up['percentage']}%")
    
    # Target domain performance
    if target_domain:
        target_results = [r for r in rows if r.get("domain") == target_domain]
        if target_results:
            target_ranks = [r.get("rank", 0) for r in target_results]
            top3_count = sum(1 for rank in target_ranks if rank <= 3)
            avg_rank = sum(target_ranks) / len(target_ranks)
            
            if top3_count > 0:
                insights.append(f"🎯 {target_domain} scored {top3_count} top-3 hits!")
            
            insights.append(f"📊 {target_domain} average rank: {avg_rank:.1f}")
    
    # AI Overview impact
    ai_count = sum(1 for r in rows if r.get("ai_overview", False))
    if ai_count > 0:
        ai_percentage = (ai_count / len(rows)) * 100
        insights.append(f"🤖 AI Overview appeared in {ai_percentage:.1f}% of results")
    
    # Rich snippet analysis
    video_count = sum(1 for r in rows if r.get("rich_snippet_type") == "video")
    shopping_count = sum(1 for r in rows if r.get("rich_snippet_type") == "shopping_pack")
    
    if video_count > 0:
        insights.append(f"🎥 {video_count} video results detected")
    
    if shopping_count > 0:
        insights.append(f"🛒 {shopping_count} shopping pack results found")
    
    # Ads analysis
    ads_count = sum(1 for r in rows if r.get("ads_slot"))
    if ads_count > 0:
        ads_percentage = (ads_count / len(rows)) * 100
        insights.append(f"💰 Ads present in {ads_percentage:.1f}% of results")
    
    return insights[:5]  # Limit to top 5 insights 