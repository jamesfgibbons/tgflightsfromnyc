"""
Parse OpenAI price query responses into structured fields for VibeNet enrichment.

Input: an OpenAI cache record (dict) or raw content JSON string.
Output: dict with {origin, destination, window_days, price_low_usd, price_high_usd,
                   typical_airlines, cited_websites, notes, brands}
Brands are derived from typical_airlines and notes via simple keyword matching.
"""
from __future__ import annotations
import json
import re
from typing import Any, Dict, List


AIRLINE_BRANDS = [
    'Delta', 'American', 'United', 'JetBlue', 'Alaska', 'Southwest', 'Spirit', 'Frontier', 'British Airways', 'Virgin Atlantic'
]


def _extract_content(rec: Dict[str, Any]) -> Dict[str, Any] | None:
    try:
        choices = rec.get('response_raw', {}).get('choices') or []
        content = choices[0].get('message', {}).get('content') if choices else None
        if not isinstance(content, str):
            return None
        data = json.loads(content)
        if not isinstance(data, dict):
            return None
        return data
    except Exception:
        return None


def _find_brands(text: str) -> List[str]:
    found = []
    for b in AIRLINE_BRANDS:
        if re.search(rf"\b{re.escape(b)}\b", text, re.IGNORECASE):
            found.append(b)
    return sorted(set(found))


def parse_price_record(cache_record: Dict[str, Any]) -> Dict[str, Any] | None:
    data = _extract_content(cache_record)
    if not data:
        return None
    origin = str(data.get('origin') or '').upper()
    dest = str(data.get('destination') or '').upper()
    window = data.get('window_days')
    low = data.get('price_low_usd')
    high = data.get('price_high_usd')
    airlines = data.get('typical_airlines') or []
    sites = data.get('cited_websites') or []
    notes = data.get('notes') or ''
    brands = _find_brands(' '.join(map(str,airlines)) + ' ' + notes)
    return {
        'origin': origin,
        'destination': dest,
        'window_days': window,
        'price_low_usd': low,
        'price_high_usd': high,
        'typical_airlines': airlines,
        'cited_websites': sites,
        'notes': notes,
        'brands': brands,
    }

