"""
Reads YAML prompt library, calls OpenAI, converts to momentum bands, and builds SonifyPlan.
"""
import os, math, json, uuid
from datetime import datetime
from typing import List, Dict, Any
import yaml
from .schemas import LLMFlightResult, SonifyPlan, MomentumBand
from .openai_client import FlightLLM
from .nostalgia import brand_to_sound_pack, routing_to_energy

def _score_from_price(midpoint: float) -> float:
    # cheaper => more positive; clamp to [-1, +1]
    if midpoint is None:
        return 0.0
    # Map $50 => +0.9; $400 => -0.7
    a, b = 50.0, 400.0
    x = max(min(midpoint, b), a)
    norm = 1 - (x - a) / (b - a)    # 1..0
    return max(-1.0, min(1.0, (norm - 0.5) * 2.0))

def _bands_from_llm(r: LLMFlightResult) -> List[MomentumBand]:
    # 8-10 segments, bias based on price midpoint & novelty
    price_mid = None
    if r.estimated_price_range and len(r.estimated_price_range)==2:
        price_mid = (r.estimated_price_range[0] + r.estimated_price_range[1]) / 2.0

    base = _score_from_price(price_mid)
    novelty = (r.novelty_score or 5)/10.0  # 0..1

    segs: List[MomentumBand] = []
    t = 0.0
    for i in range(10):
        jitter = (novelty - 0.5) * 0.4
        score = max(-1.0, min(1.0, base + (i-4)*0.03 + jitter))
        label = "positive" if score > 0.15 else "negative" if score < -0.15 else "neutral"
        segs.append(MomentumBand(t0=t, t1=t+3.2, label=label, score=round(score, 3)))
        t += 3.2
    return segs

def _label_summary(segs: List[MomentumBand]) -> Dict[str,int]:
    s = {"positive":0,"neutral":0,"negative":0}
    for b in segs:
        s[b.label]+=1
    return s

def build_plans_from_yaml(yaml_path: str, limit: int = 40) -> List[Dict[str,Any]]:
    with open(yaml_path,"r") as f:
        lib = yaml.safe_load(f)
    origins = lib["origins"]
    dests = lib["destinations"]
    templates = lib["templates"]
    specials = lib.get("novelty_special",[])

    prompts=[]
    for o in origins:
        for d in dests:
            for tpl in templates:
                prompts.append({
                    "origin": o,
                    "destination": d["code"],
                    "title": f"{o}->{d['code']}",
                    "prompt": tpl.format(origin=o, dest=d["name"])
                })
    for s in specials:
        prompts.append({
            "origin": "NYC_ALL",
            "destination": "LAS",
            "title": "NYC_ALL->LAS SPECIAL",
            "prompt": s
        })

    if limit:
        prompts = prompts[:limit]

    llm = FlightLLM()
    plans=[]
    for p in prompts:
        data = llm.analyze_prompt(p["prompt"])
        r = LLMFlightResult(
            origin=p["origin"], destination=p["destination"], prompt=p["prompt"], **data
        )
        segs = _bands_from_llm(r)
        label_summary = _label_summary(segs)

        brand_hint = r.carrier_likelihood[0] if r.carrier_likelihood else p["destination"]
        pack = brand_to_sound_pack(str(brand_hint))
        tempo, bars = routing_to_energy(r.routing_strategy or "direct")

        plan = SonifyPlan(
            sound_pack=pack, total_bars=bars, tempo_base=tempo, key_hint=None,
            momentum=segs, label_summary=label_summary
        )
        plans.append({
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "channel": "travel",
            "brand": brand_hint,
            "title": p["title"],
            "prompt": p["prompt"],
            "plan": plan.model_dump()
        })
    return plans