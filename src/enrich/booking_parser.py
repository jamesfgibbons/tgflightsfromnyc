"""
Parse OpenAI booking-window responses into structured fields for VibeNet enrichment.

Expected content JSON fields:
- origin, destination, window_days
- best_window_days: [min, max]
- fare_low_usd, fare_high_usd
- notes
"""
from __future__ import annotations
import json
from typing import Any, Dict


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


def parse_booking_record(cache_record: Dict[str, Any]) -> Dict[str, Any] | None:
    data = _extract_content(cache_record)
    if not data:
        return None
    return {
        'origin': (data.get('origin') or '').upper(),
        'destination': (data.get('destination') or '').upper(),
        'window_days': data.get('window_days'),
        'best_window_days': data.get('best_window_days'),
        'fare_low_usd': data.get('fare_low_usd'),
        'fare_high_usd': data.get('fare_high_usd'),
        'notes': data.get('notes') or ''
    }

