#!/usr/bin/env python3
"""
Conversational cache builder:
- Runs web search via Tavily (or returns empty if key missing)
- Calls OpenAI to produce a concise analyst note + a SIGNALS YAML block
- Upserts both into Supabase (visibility_notes + visibility_signals)
"""
import os, sys, time, uuid, json, datetime as dt
from typing import List, Dict
from dataclasses import asdict

import requests
from tqdm import tqdm
from dateutil import tz

from openai import OpenAI
from ..config import settings
from ..searchers.tavily_client import web_search
from .utils import extract_yaml_or_json_block

# ------------------------------
# Simple geo registry (NYC + Caribbean)
NYC_AIRPORTS = ["JFK","LGA","EWR","HPN","ISP","SWF"]
CARIBBEAN_AIRPORTS = ["SJU","AUA","CUR","BGI","NAS","MBJ","PLS","GCM","SXM","PUJ","SDQ","ANU","STT","STX","GND","DOM","SKB","EIS","BON","PTP","FDF"]

# ------------------------------
# Supabase client (minimal, HTTP)
class Supa:
    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.key = key
    def upsert(self, table: str, rows: List[dict], on_conflict: str = None):
        if not rows: return {"count":0}
        # PostgREST upsert is insert + on_conflict header
        endpoint = f"{self.url}/rest/v1/{table}"
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        if on_conflict:
            headers["Prefer"] += f",resolution=merge-duplicates"
            endpoint += f"?on_conflict={on_conflict}"
        r = requests.post(endpoint, headers=headers, json=rows, timeout=60)
        if r.status_code >= 300:
            raise RuntimeError(f"Supabase upsert failed: {r.status_code} {r.text}")
        return r.json()

supa = Supa(settings.supabase_url, settings.supabase_key)

# ------------------------------
def build_query(origin_metro: str, dest_airport: str, date_phrase: str) -> str:
    return (
        f"Cheapest one-way flight from any {origin_metro} airport to {dest_airport} {date_phrase}. "
        f"Look for rock-bottom fares, red-eye options, and which airline/seller is likely to have it. "
        f"Return a short, human-readable analyst note (~120 words) with citations, then append a SIGNALS YAML block "
        f"containing: price_low_est, price_typical_est, price_high_est, red_eye_share_est (0..1), "
        f"carriers_mentioned, sellers_mentioned, novelty_notes, confidence (0..1), citations (urls)."
    )

SYSTEM_MSG = (
    "You are a concise airfare research analyst. Use the provided web sources as your primary evidence. "
    "Write like a human, avoid hedging beyond one brief disclaimer. Cite sources inline as [#] where # is the source index. "
    "After your short note, append a fenced YAML code-block named SIGNALS with the fields exactly as specified. "
    "If a field is unknown, set it to null. Keep prices in USD."
)

def compose_messages(sources: List[Dict], question: str):
    # Present sources as a ranked list
    src_lines = []
    for i, s in enumerate(sources, start=1):
        title = s.get("title") or "Untitled"
        url = s.get("url") or ""
        snippet = (s.get("content") or "")[:240].replace("\n", " ").strip()
        src_lines.append(f"[{i}] {title} — {url}\n    {snippet}")
    src_blob = "\n".join(src_lines) if src_lines else "No sources were available."
    user = (
        f"SOURCES:\n{src_blob}\n\n"
        f"QUESTION:\n{question}\n\n"
        "RESPONSE FORMAT:\n"
        "1) A 80–140 word natural-language analyst note with inline citations like [1], [2].\n"
        "2) Then a YAML block fenced as ```yaml and starting with 'SIGNALS:' and the keys listed.\n"
        "   Example:\n"
        "```yaml\nSIGNALS:\n  price_low_est: 78\n  price_typical_est: 115\n"
        "  price_high_est: 240\n  red_eye_share_est: 0.35\n  carriers_mentioned: ["JetBlue","Frontier"]\n"
        "  sellers_mentioned: ["JetBlue.com","Expedia"]\n  novelty_notes: ["NYC-wide rock-bottom under $90"]\n"
        "  confidence: 0.63\n  citations: ["https://...","https://..."]\n```"
    )
    return [
        {"role":"system", "content": SYSTEM_MSG},
        {"role":"user", "content": user}
    ]

def openai_client():
    return OpenAI(api_key=settings.openai_api_key)

def ask_llm(messages):
    if settings.mock:
        # Produce a deterministic mock response with a YAML block
        text = (
            "Cheapest NYC→Caribbean notes (mock). Likely JetBlue or Frontier has a sub-$100 fare [1].\n\n"
            "```yaml\nSIGNALS:\n  price_low_est: 89\n  price_typical_est: 139\n  price_high_est: 259\n"
            "  red_eye_share_est: 0.4\n  carriers_mentioned: [\"JetBlue\",\"Frontier\"]\n"
            "  sellers_mentioned: [\"JetBlue.com\",\"Expedia\"]\n  novelty_notes: [\"NYC-wide rock-bottom\"]\n"
            "  confidence: 0.55\n  citations: [\"https://example.com\"]\n```"
        )
        return text
    client = openai_client()
    resp = client.chat.completions.create(
        model=settings.model,
        temperature=settings.temperature,
        messages=messages,
        max_tokens=settings.max_output_tokens
    )
    return resp.choices[0].message.content

def upsert_records(origin_metro: str, dest_airport: str, question: str, date_today: str, response_text: str, signals: dict):
    run_id = settings.run_id or dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    # Notes table
    notes_row = {
        "origin_metro": origin_metro,
        "destination": dest_airport,
        "asked_on": date_today,
        "note_text": response_text[:8000],
        "citations": json.dumps(signals.get("citations") or []),
        "run_id": run_id,
    }
    # Signals table
    sig_row = {
        "origin_metro": origin_metro,
        "destination": dest_airport,
        "asked_on": date_today,
        "price_low_est": signals.get("price_low_est"),
        "price_typical_est": signals.get("price_typical_est"),
        "price_high_est": signals.get("price_high_est"),
        "red_eye_share_est": signals.get("red_eye_share_est"),
        "carriers": json.dumps(signals.get("carriers_mentioned") or []),
        "sellers": json.dumps(signals.get("sellers_mentioned") or []),
        "novelty_notes": json.dumps(signals.get("novelty_notes") or []),
        "confidence": signals.get("confidence"),
        "run_id": run_id,
    }
    supa.upsert("visibility_notes", [notes_row], on_conflict="origin_metro,destination,asked_on,run_id")
    supa.upsert("visibility_signals", [sig_row], on_conflict="origin_metro,destination,asked_on,run_id")

def run(day_phrase: str = "tomorrow", max_dests: int = 10, max_results_per_query: int = 5):
    settings.assert_minimum()
    origin_metro = "NYC"
    date_today = dt.date.today().isoformat()

    # Limit destinations to make first run fast
    destinations = CARIBBEAN_AIRPORTS[:max_dests]
    for dest in tqdm(destinations, desc="Destinations"):
        q = build_query(origin_metro, dest, day_phrase)
        # web search
        sources = web_search(f"{origin_metro} to {dest} cheapest one way {day_phrase}", settings.search_api_key, max_results=max_results_per_query)
        # LLM messages
        msgs = compose_messages(sources, q)
        text = ask_llm(msgs)
        signals_doc = extract_yaml_or_json_block(text) or {}
        signals = signals_doc.get("SIGNALS") if isinstance(signals_doc, dict) else {}
        if not signals:
            # Attempt direct keys (if the YAML lacks 'SIGNALS:' root)
            signals = signals_doc or {}
        upsert_records(origin_metro, dest, q, date_today, text, signals)
        time.sleep(0.3)  # be a good API citizen

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", default="tomorrow", help="e.g., 'tomorrow', 'this weekend', 'next month'")
    ap.add_argument("--max-dests", type=int, default=10)
    ap.add_argument("--max-results", type=int, default=5, help="web results per query")
    args = ap.parse_args()
    run(day_phrase=args.day, max_dests=args.max_dests, max_results_per_query=args.max_results)
