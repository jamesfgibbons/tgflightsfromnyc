import argparse
import datetime as dt
import re
import json
import os
from typing import List, Dict
from dateutil import parser as dparser

from .schemas import OFFER_JSON_SCHEMA
from ..config import settings
from ..supabase_io import upsert_offers
from ..openai_client import structured_offers_from_openai

BRAND_ALIASES = {
    "jetblue": ("JetBlue", "B6"),
    "american": ("American Airlines", "AA"),
    "delta": ("Delta Air Lines", "DL"),
    "united": ("United Airlines", "UA"),
    "spirit": ("Spirit Airlines", "NK"),
    "frontier": ("Frontier Airlines", "F9"),
    "caribbean airlines": ("Caribbean Airlines", "BW"),
    "cayman airways": ("Cayman Airways", "KX"),
    "bahamasair": ("Bahamasair", "UP"),
    "air caraibes": ("Air Caraïbes", "TX"),
    "intercaribbean": ("InterCaribbean Airways", "JY"),
    "copa": ("Copa Airlines", "CM"),
}

IATA_CITY_TO_AIRPORT = {
    "NYC": "JFK"  # Default NYC to JFK
}

def _canon_airport(code: str) -> str:
    code = (code or "").upper().strip()
    return IATA_CITY_TO_AIRPORT.get(code, code)

def _canon_brand(name: str) -> tuple:
    if not name: 
        return None, None
    k = re.sub(r"[^a-z]+", "", name.lower())
    return BRAND_ALIASES.get(k, (name.strip(), None))

def _safe_date(text: str, base: dt.date) -> str:
    """Parse date text with year rollover logic"""
    if not text:
        return base.isoformat()
    
    text = text.replace("–", "-").replace("—", "-")
    try:
        # Parse with base year
        d = dparser.parse(text, default=dt.datetime(base.year, 1, 1)).date()
        # If parsed date is more than 9 months in the past, assume next year
        if d < base and (base - d).days > 270:
            d = dt.date(base.year + 1, d.month, d.day)
        return d.isoformat()
    except Exception:
        return base.isoformat()

def _regex_fallback(raw: str, today: dt.date) -> List[Dict]:
    """Regex fallback parser for unstructured text"""
    offers = []
    # Pattern: "JFK → STT JetBlue $129 on Aug 23 (nonstop)"
    line_re = re.compile(
        r'(?P<origin>[A-Za-z]{3})\s*[→->]\s*(?P<dst>[A-Za-z]{3}).*?(?P<brand>[A-Za-z ]+?)\s*\$?(?P<price>\d{2,4})(?:\s*USD)?\s*(?:on|for|/)?\s*(?P<date>[A-Za-z0-9\-–, ]+)?',
        re.I
    )
    
    for m in line_re.finditer(raw):
        origin = _canon_airport(m.group("origin"))
        dest = _canon_airport(m.group("dst"))
        brand_name, brand_code = _canon_brand(m.group("brand"))
        price = float(m.group("price"))
        dep = _safe_date(m.group("date") or "", today)
        
        offers.append({
            "origin": origin,
            "destination": dest,
            "brand": brand_name,
            "brand_code": brand_code,
            "price": price,
            "currency": "USD",
            "nonstop": True,
            "fare_type": "unknown",
            "departure_date": dep,
            "notes": "regex_fallback",
            "approximate": False
        })
    
    return offers

def build_prompt(days: int) -> str:
    today = dt.date.today()
    start_date = (today - dt.timedelta(days=days//2)).isoformat()
    end_date = (today + dt.timedelta(days=days//2)).isoformat()
    
    return f"""
Find flight offers from NYC airports (JFK/LGA/EWR) to Caribbean destinations between {start_date} and {end_date}.

Caribbean destinations include: SJU, STT, STX, SDQ, PUJ, POP, STI, MBJ, KIN, HAV, AUA, CUR, BON, BGI, ANU, SKB, EIS, DOM, GND, SXM, PTP, FDF, NAS, GGT, ELH, FPO, GCM, PLS.

Return ONLY valid JSON with flight offers. Each offer must include:
- origin: IATA code (use JFK for NYC)
- destination: IATA code 
- brand: airline name (e.g., "JetBlue")
- brand_code: IATA airline code if known (e.g., "B6")
- price: numeric fare in USD
- currency: "USD"
- departure_date: YYYY-MM-DD format
- nonstop: true/false
- approximate: true if price is "under $X" or "about $X"

Focus on realistic current pricing for nonstop flights. Include a mix of budget and premium carriers.
"""

def run(days: int = 14, cache_path: str = "data/openai_cache.jsonl"):
    settings.assert_minimum()
    
    today = dt.date.today()
    prompt = build_prompt(days)
    
    try:
        print(f"🤖 Calling OpenAI for structured flight offers (days={days})")
        data = structured_offers_from_openai(prompt, OFFER_JSON_SCHEMA)
        offers = data.get("offers", [])
        source = "openai-structured"
        print(f"✅ OpenAI returned {len(offers)} structured offers")
        
    except Exception as e:
        print(f"⚠️ Structured call failed ({e}); attempting regex fallback from cache...")
        offers = []
        raw_texts = []
        
        if os.path.exists(cache_path):
            with open(cache_path) as f:
                for line in f:
                    try:
                        raw_texts.append(json.loads(line)["response_text"])
                    except Exception:
                        pass
        
        for raw in raw_texts:
            offers.extend(_regex_fallback(raw, today))
        
        source = "openai-regex-fallback"
        print(f"⚠️ Fallback extracted {len(offers)} offers from cache")
    
    if not offers:
        print("❌ No offers extracted - check OpenAI API key and prompt")
        return
    
    # Canonicalize and normalize
    normalized = []
    for o in offers:
        brand_name, brand_code = _canon_brand(o.get("brand"))
        
        normalized_offer = {
            "origin": _canon_airport(o.get("origin")),
            "destination": _canon_airport(o.get("destination")),
            "brand": brand_name or "Unknown",
            "brand_code": o.get("brand_code") or brand_code,
            "currency": (o.get("currency") or "USD").upper(),
            "price_cents": int(round(float(o.get("price", 0)) * 100)),
            "nonstop": o.get("nonstop", True),
            "fare_type": o.get("fare_type", "unknown"),
            "departure_date": o.get("departure_date", today.isoformat()),
            "approximate": o.get("approximate", False),
            "notes": o.get("notes", "")
        }
        normalized.append(normalized_offer)
    
    # Upsert to Supabase
    print(f"💾 Upserting {len(normalized)} normalized offers to Supabase...")
    upsert_offers(normalized, source=source)
    print(f"🎉 Pipeline step 1 complete: {len(normalized)} offers from {source}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--cache-path", type=str, default="data/openai_cache.jsonl")
    args = ap.parse_args()
    run(days=args.days, cache_path=args.cache_path)