"""
LLM wrapper for structured flight analysis (xAI Grok-first, then Groq, then OpenAI).
"""
import os, json
from typing import Dict, Any, Optional
from datetime import datetime
import logging

import requests

SYSTEM_PROMPT = """You are a flight price analysis expert.
Return STRICT JSON with fields:
estimated_price_range: [min,max] USD, best_booking_window (int days),
peak_discount_times: array of phrases, carrier_likelihood: array of airlines,
routing_strategy: one of direct, connecting, hidden-city, multi-city,
novelty_score: 1-10, sonification_params: { frequency_hint_hz, rhythm_hint, amplitude_hint }.
If uncertain, provide reasoned conservative estimates.
"""

logger = logging.getLogger(__name__)


def _xai_available() -> bool:
    # Treat GROK and xAI as the same provider
    return bool(os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY"))


def _groq_client():
    try:
        from groq import Groq
    except Exception:
        return None
    key = os.getenv("GROQ_API_KEY") or os.getenv("GROK_API_KEY")
    if not key:
        return None
    return Groq(api_key=key)


def _openai_client():
    try:
        from openai import OpenAI
    except Exception:
        return None
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    return OpenAI(api_key=key)


class FlightLLM:
    def __init__(self):
        # Provider preference: xAI → Groq → OpenAI
        self.use_xai = _xai_available()
        self.groq = None if self.use_xai else _groq_client()
        self.openai = None if (self.use_xai or self.groq) else _openai_client()
        if not (self.use_xai or self.groq or self.openai):
            raise RuntimeError("Set XAI_API_KEY or GROQ_API_KEY or OPENAI_API_KEY")
        # Model overrides via GROK_MODEL or XAI_MODEL
        self.xai_model = os.getenv("GROK_MODEL") or os.getenv("XAI_MODEL") or "grok-beta"
        self.groq_model = os.getenv("GROQ_TEXT_MODEL", "llama-3.1-8b-instant")
        self.oa_model = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")

    def analyze_prompt(self, prompt: str) -> Dict[str, Any]:
        if self.use_xai:
            raw = self._call_xai(prompt)
        elif self.groq:
            resp = self.groq.chat.completions.create(
                model=self.groq_model,
                temperature=0.3,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            raw = resp.choices[0].message.content
        else:
            resp = self.openai.chat.completions.create(
                model=self.oa_model,
                temperature=0.3,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
            raw = resp.choices[0].message.content
        data = json.loads(raw)
        data["timestamp"] = datetime.utcnow().isoformat()
        return data

    def _call_xai(self, prompt: str) -> str:
        """Call xAI Chat Completions API directly.

        Uses OpenAI-compatible schema: POST https://api.x.ai/v1/chat/completions
        Expects a JSON-only response body (SYSTEM_PROMPT enforces this).
        """
        url = os.getenv("XAI_BASE_URL", "https://api.x.ai/v1/chat/completions")
        key = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")
        if not key:
            raise RuntimeError("XAI_API_KEY not set")
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.xai_model,
            "temperature": 0.3,
            # Some xAI deployments may not support OpenAI's response_format yet; SYSTEM_PROMPT enforces JSON.
            # "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        }
        try:
            r = requests.post(url, headers=headers, json=body, timeout=60)
            r.raise_for_status()
            j = r.json()
            raw = j["choices"][0]["message"]["content"]
            return raw
        except Exception as e:
            logger.error(f"xAI request failed: {e}")
            raise
