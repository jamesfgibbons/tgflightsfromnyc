"""
OpenAI wrapper for structured flight analysis.
"""
import os, json
from typing import Dict, Any
from datetime import datetime
from openai import OpenAI

SYSTEM_PROMPT = """You are a flight price analysis expert.
Return STRICT JSON with fields:
estimated_price_range: [min,max] USD, best_booking_window (int days),
peak_discount_times: array of phrases, carrier_likelihood: array of airlines,
routing_strategy: one of direct, connecting, hidden-city, multi-city,
novelty_score: 1-10, sonification_params: { frequency_hint_hz, rhythm_hint, amplitude_hint }.
If uncertain, provide reasoned conservative estimates.
"""

class FlightLLM:
    def __init__(self):
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set")
        self.client = OpenAI(api_key=key)

    def analyze_prompt(self, prompt: str) -> Dict[str, Any]:
        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            response_format={"type":"json_object"},
            messages=[
                {"role":"system","content": SYSTEM_PROMPT},
                {"role":"user","content": prompt}
            ]
        )
        raw = resp.choices[0].message.content
        data = json.loads(raw)
        data["timestamp"] = datetime.utcnow().isoformat()
        return data