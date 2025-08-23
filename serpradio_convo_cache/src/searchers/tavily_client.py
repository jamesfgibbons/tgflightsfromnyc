import os, requests, time

API_URL = "https://api.tavily.com/search"  # simple, fast search API

def web_search(query: str, api_key: str, max_results: int = 5, timeout: int = 30):
    if not api_key:
        # No key provided - return empty result so pipeline still works
        return []
    try:
        payload = {
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": max_results,
        }
        r = requests.post(API_URL, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json() or {}
        results = data.get("results", []) or []
        # Normalize fields we care about
        norm = []
        for i, x in enumerate(results):
            norm.append({
                "rank": i + 1,
                "title": x.get("title"),
                "url": x.get("url"),
                "content": x.get("content") or x.get("snippet"),
            })
        return norm
    except Exception as e:
        print(f"⚠️ web_search failed for '{query}': {e}")
        return []
