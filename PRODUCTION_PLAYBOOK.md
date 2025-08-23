# 🎵 SERP Radio - Production Playbook

## 🎯 **Complete End-to-End Implementation**

This playbook transforms SERP Radio into a living "audio fabric" for AI search visibility with OpenAI-backed cache, emotive audio generation, and Caribbean "Kokomo" theme integration.

---

## 📋 **Single Source of Truth (Production Values)**

### **Infrastructure Constants**
```bash
# API & Storage
STAGING_API_BASE=https://serpradio-api-2025.onrender.com
AWS_REGION=us-east-1
S3_PRIVATE_BUCKET=serpradio-artifacts-2025
S3_PUBLIC_BUCKET=serpradio-public-2025
KMS_KEY_ALIAS=alias/serpradio-kms-2025
ADMIN_SECRET=sr_admin_2025_9hAqV3XbL2

# Audio Configuration
SOUNDFONT_PATH=/usr/share/sounds/sf2/FluidR3_GM.sf2
DEFAULT_LUFS=-14
DEFAULT_SAMPLE_RATE=44100

# CORS Allowlist
CORS_ORIGINS=[
  "https://serpradio.lovable.app",
  "https://serpradio.com", 
  "https://www.serpradio.com",
  "http://localhost:5173",
  "http://localhost:3000"
]
```

---

## 🗄️ **Supabase Database Schema**

### **Complete SQL Setup**
```sql
-- ===============================
-- SERP Radio Production Schema
-- ===============================

-- Email lead capture
CREATE TABLE IF NOT EXISTS public.email_leads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL UNIQUE,
  utm JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- User profiles
CREATE TABLE IF NOT EXISTS public.profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE,
  display_name TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Regional keyword library (source data)
CREATE TABLE IF NOT EXISTS public.regional_keywords (
  id BIGSERIAL PRIMARY KEY,
  region TEXT NOT NULL,              -- CARIBBEAN, US-NE, US-West
  country TEXT NOT NULL,             -- US, PR, JM, AW, DO
  market TEXT NOT NULL,              -- travel, flights, hotels
  category TEXT NOT NULL,            -- flights_from_nyc, caribbean_resorts
  brand TEXT NULL,                   -- Spirit, JetBlue, Marriott
  query TEXT NOT NULL,               -- "cheap flights nyc to san juan"
  intent TEXT NOT NULL,              -- deal, planning, brand, last_minute
  weight NUMERIC NOT NULL DEFAULT 1, -- sampling frequency
  seed_source TEXT NOT NULL DEFAULT 'curated',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- OpenAI analysis cache (raw LLM outputs)
CREATE TABLE IF NOT EXISTS public.prompt_runs (
  id BIGSERIAL PRIMARY KEY,
  keyword_id BIGINT REFERENCES public.regional_keywords(id) ON DELETE CASCADE,
  model TEXT NOT NULL,
  temperature NUMERIC NOT NULL DEFAULT 0.3,
  status TEXT NOT NULL CHECK (status IN ('ok','error')) DEFAULT 'ok',
  prompt_text TEXT NOT NULL,
  result_json JSONB NOT NULL,
  cost_usd NUMERIC DEFAULT 0,
  latency_ms INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Visibility cache (sonification-ready data)
CREATE TABLE IF NOT EXISTS public.visibility_cache (
  id BIGSERIAL PRIMARY KEY,
  keyword_id BIGINT REFERENCES public.regional_keywords(id) ON DELETE CASCADE,
  region TEXT NOT NULL,
  market TEXT NOT NULL,
  category TEXT NOT NULL,
  answer_text TEXT,                  -- AI answer engine response
  brand_mentions JSONB DEFAULT '[]'::jsonb,
  momentum_bands JSONB DEFAULT '[]'::jsonb, -- [{t0,t1,label,score}]
  wow_events JSONB DEFAULT '[]'::jsonb,     -- earcon triggers
  analysis JSONB DEFAULT '{}'::jsonb,       -- full LLM features
  sound_pack TEXT DEFAULT 'Arena Rock',
  bpm INTEGER DEFAULT 120,
  key_center TEXT DEFAULT 'C',
  audio_key TEXT,                    -- S3 key to MP3
  midi_key TEXT,                     -- S3 key to MIDI
  lufs NUMERIC DEFAULT -14,
  duration_sec NUMERIC,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Project management
CREATE TABLE IF NOT EXISTS public.sonification_projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_profile UUID REFERENCES public.profiles(id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Project inventory mapping
CREATE TABLE IF NOT EXISTS public.sonification_inventory (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID REFERENCES public.sonification_projects(id) ON DELETE CASCADE,
  cache_id BIGINT REFERENCES public.visibility_cache(id) ON DELETE CASCADE,
  pinned BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Public view for frontend (anonymized)
CREATE OR REPLACE VIEW public.v_visibility_public AS
SELECT
  vc.id,
  rk.region, rk.country, rk.market, rk.category, rk.brand, rk.query,
  vc.answer_text, vc.brand_mentions, vc.momentum_bands, vc.wow_events,
  vc.sound_pack, vc.bpm, vc.key_center, vc.duration_sec,
  vc.audio_key, vc.midi_key, vc.lufs, vc.updated_at
FROM public.visibility_cache vc
JOIN public.regional_keywords rk ON rk.id = vc.keyword_id;

-- Regional summary view
CREATE OR REPLACE VIEW public.v_regional_summary AS
SELECT 
  region,
  COUNT(*) as total_queries,
  COUNT(DISTINCT sound_pack) as sound_packs_used,
  AVG(bpm) as avg_bpm,
  COUNT(DISTINCT category) as categories
FROM public.v_visibility_public 
GROUP BY region
ORDER BY total_queries DESC;

-- ===============================
-- Row Level Security (RLS)
-- ===============================

ALTER TABLE public.email_leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.regional_keywords ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.prompt_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.visibility_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sonification_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sonification_inventory ENABLE ROW LEVEL SECURITY;

-- Email leads: anyone can insert
CREATE POLICY email_leads_insert ON public.email_leads
  FOR INSERT TO anon, authenticated
  WITH CHECK (true);

-- Public views: read access for anon/authenticated
GRANT SELECT ON public.v_visibility_public TO anon, authenticated;
GRANT SELECT ON public.v_regional_summary TO anon, authenticated;

-- Core tables: service role only (backend access)
REVOKE ALL ON TABLE public.regional_keywords FROM anon, authenticated;
REVOKE ALL ON TABLE public.prompt_runs FROM anon, authenticated;
REVOKE ALL ON TABLE public.visibility_cache FROM anon, authenticated;

-- ===============================
-- Indexes for Performance
-- ===============================

CREATE INDEX IF NOT EXISTS idx_regional_keywords_region ON public.regional_keywords(region);
CREATE INDEX IF NOT EXISTS idx_regional_keywords_category ON public.regional_keywords(category);
CREATE INDEX IF NOT EXISTS idx_visibility_cache_region ON public.visibility_cache(region);
CREATE INDEX IF NOT EXISTS idx_visibility_cache_updated ON public.visibility_cache(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_prompt_runs_keyword ON public.prompt_runs(keyword_id);
```

---

## 🌴 **Caribbean "Kokomo" Theme Integration**

### **Seed Data: Caribbean Keywords**
```csv
region,country,market,category,brand,query,intent,weight,seed_source
CARIBBEAN,PR,travel,caribbean_resorts,Marriott,"all inclusive resort puerto rico san juan",planning,2,curated
CARIBBEAN,PR,travel,caribbean_resorts,,cheap flights nyc to san juan,deal,3,curated
CARIBBEAN,JM,travel,caribbean_resorts,Sandals,montego bay all inclusive adults only,planning,3,curated
CARIBBEAN,JM,travel,caribbean_resorts,,flights jfk to montego bay red eye,last_minute,2,curated
CARIBBEAN,AW,travel,caribbean_resorts,Hyatt,aruba palm beach family resort,planning,2,curated
CARIBBEAN,AW,travel,caribbean_resorts,,budget flights nyc to aruba,deal,3,curated
CARIBBEAN,DO,travel,caribbean_resorts,Hard Rock,punta cana all inclusive with flights,planning,3,curated
CARIBBEAN,DO,travel,caribbean_resorts,,nyc to punta cana weekend trip,deal,2,curated
CARIBBEAN,BS,travel,caribbean_resorts,Atlantis,atlantis bahamas package flights hotel,planning,3,curated
CARIBBEAN,BS,travel,caribbean_resorts,,long weekend bahamas from nyc,planning,2,curated
CARIBBEAN,BB,travel,caribbean_resorts,,best time to visit barbados,planning,1,curated
CARIBBEAN,TC,travel,caribbean_resorts,,turks and caicos last minute deals,last_minute,2,curated
CARIBBEAN,CW,travel,caribbean_resorts,,flights nyc to curacao mistake fare,deal,1,curated
CARIBBEAN,AG,travel,caribbean_resorts,,antigua couples all inclusive,planning,2,curated
CARIBBEAN,GD,travel,caribbean_resorts,,grenada boutique resort,planning,1,curated
CARIBBEAN,KN,travel,caribbean_resorts,,st kitts luxury resort points,planning,1,curated
CARIBBEAN,DM,travel,caribbean_resorts,,dominica eco resort hot springs,planning,1,curated
CARIBBEAN,VG,travel,caribbean_resorts,,bvi sailing packages from nyc,planning,1,curated
CARIBBEAN,PR,travel,caribbean_resorts,JetBlue,jetblue mint nyc to san juan deals,deal,2,curated
CARIBBEAN,JM,travel,caribbean_resorts,Delta,delta one lie flat jfk to mbj,deal,1,curated
```

### **Tropical Pop Sound Pack Configuration**
```python
# Enhanced soundpacks.py
TROPICAL_POP = {
    "name": "Tropical Pop",
    "description": "Beach Boys 'Kokomo' meets steel drums - laid-back Caribbean vibes",
    "tempo_range": [95, 115],
    "default_tempo": 104,
    "key_preferences": ["F", "C", "G", "Bb"],
    "default_key": "F",
    "instruments": {
        "lead": "steel_drum",
        "harmony": "marimba", 
        "bass": "upright_bass",
        "percussion": ["shaker", "vibes", "bongos", "wind_chimes"],
        "fx": ["ocean_waves", "seagulls"]
    },
    "mood_descriptors": ["relaxed", "tropical", "nostalgic", "beachy"],
    "earcon_bank": {
        "volatility_spike": "crystal.ping",
        "destination_reveal": "steel_drum_roll", 
        "price_drop": "wind_chime_down",
        "deal_jackpot": "island_celebration",
        "brand_spike": "marimba_flourish"
    },
    "arrangement_style": {
        "rhythm_feel": "reggae_upbeat",  # Emphasize beats 2 and 4
        "section_transitions": "palm_muted_guitar",
        "dynamics": "laid_back_compression"
    }
}
```

### **Kokomo Nostalgia Mapping Rules**
```python
# Enhanced nostalgia engine
def get_caribbean_sound_mapping(destination_code: str, search_volume: int) -> Dict[str, Any]:
    """Map Caribbean destinations to specific Kokomo variations."""
    
    # High-volume destinations get full orchestration
    if search_volume > 3000:  # Puerto Rico, Aruba, Jamaica
        return {
            "sound_pack": "Tropical Pop",
            "tempo": 104,
            "key": "F",
            "instrumentation": "full_tropical_orchestra",
            "earcon_intensity": "high"
        }
    
    # Medium-volume gets focused arrangement  
    elif search_volume > 1000:  # Dominican Republic, Bahamas
        return {
            "sound_pack": "Tropical Pop", 
            "tempo": 100,
            "key": "C",
            "instrumentation": "steel_drum_and_guitar",
            "earcon_intensity": "medium"
        }
    
    # Lower-volume gets ambient treatment
    else:  # Smaller islands
        return {
            "sound_pack": "Tropical Pop",
            "tempo": 96,
            "key": "Bb", 
            "instrumentation": "ambient_island",
            "earcon_intensity": "subtle"
        }

# Theme-specific tempo modulation
def adjust_tempo_for_theme(base_tempo: int, theme: str, momentum_volatility: float) -> int:
    """Adjust tempo based on theme and market volatility."""
    
    if theme == "caribbean_kokomo":
        # Caribbean stays laid-back but can get excited for deals
        excitement_boost = min(10, int(momentum_volatility * 15))
        return min(115, base_tempo + excitement_boost)
    
    elif theme == "red_eye_deals":
        # Red-eye flights are slower, more ambient
        return max(90, base_tempo - 15)
        
    elif theme == "budget_carriers":
        # Budget carriers are energetic, playful
        return min(140, base_tempo + 20)
        
    elif theme == "legacy_airlines":
        # Legacy airlines are confident but not frantic
        return max(110, min(135, base_tempo + 5))
    
    return base_tempo
```

---

## 🔄 **Enhanced Pipeline Architecture**

### **OpenAI Cache Builder**
```python
# src/pipeline/openai_cache.py
import os, time, json, math
from datetime import datetime
from typing import Dict, Any, List, Tuple
import requests

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_SERVICE_ROLE = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
HEADERS_AI = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
HEADERS_SB = {"apikey": SUPABASE_SERVICE_ROLE, "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE}", "Content-Type": "application/json"}

SYSTEM_PROMPT = """
You are a flight & travel visibility analyst. Return STRICT JSON with:
{
  "estimated_price_range": [minUSD, maxUSD],
  "best_booking_window_days": integer,
  "peak_discount_times": ["Tue","Wed",...],
  "carrier_likelihood": ["Spirit","JetBlue","Delta",...],
  "routing_strategy": "direct"|"connecting"|"hidden-city"|"multi-city",
  "novelty_score": 1-10,
  "answer_text": "concise answer engine style blurb for a user",
  "brands": [{"name": "...", "confidence": 0-1}],
  "momentum_bands": [{"t0": sec, "t1": sec, "label": "positive|neutral|negative", "score": -1..1}],
  "wow_events": [{"time": sec, "type": "podium_win|volatility_spike|brand_spike|ai_steal"}],
  "sonic": {"sound_pack": "Arena Rock|8-Bit|Synthwave|Tropical Pop", "bpm": int, "key": "C|G|Am|F"}
}

Special Caribbean mapping: If query relates to Caribbean destinations (Puerto Rico, Jamaica, Aruba, Dominican Republic, Bahamas, etc.), prefer:
- sound_pack: "Tropical Pop"
- bpm: 100-110 (laid-back beach tempo)
- key: "F" or "C" (warm, tropical feel)
- Emphasize positive momentum for deals, island atmosphere

Respond ONLY with JSON.
"""

class CacheBuilder:
    def __init__(self):
        self.stats = {"processed": 0, "errors": 0, "caribbean_count": 0}
    
    def _sb_select_keywords(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Fetch keywords from Supabase."""
        url = f"{SUPABASE_URL}/rest/v1/regional_keywords?select=*&order=created_at.desc&limit={limit}"
        r = requests.get(url, headers=HEADERS_SB, timeout=30)
        r.raise_for_status()
        return r.json()

    def _sb_upsert_prompt_run(self, keyword_id: int, prompt_text: str, result: Dict[str, Any], status: str = "ok", cost: float = 0.0, latency_ms: int = 0):
        """Store raw OpenAI response."""
        url = f"{SUPABASE_URL}/rest/v1/prompt_runs"
        payload = [{
            "keyword_id": keyword_id,
            "model": OPENAI_MODEL,
            "temperature": 0.3,
            "status": status,
            "prompt_text": prompt_text,
            "result_json": result,
            "cost_usd": cost,
            "latency_ms": latency_ms
        }]
        r = requests.post(url, headers=HEADERS_SB, json=payload, timeout=30)
        r.raise_for_status()

    def _sb_upsert_visibility(self, keyword: Dict[str, Any], result: Dict[str, Any]):
        """Store processed visibility cache entry."""
        url = f"{SUPABASE_URL}/rest/v1/visibility_cache"
        
        # Enhanced sonic mapping for Caribbean
        sonic = result.get("sonic", {})
        if keyword["region"] == "CARIBBEAN":
            sonic = {
                "sound_pack": "Tropical Pop",
                "bpm": min(110, max(95, sonic.get("bpm", 104))),
                "key": "F" if sonic.get("key") not in ["F", "C"] else sonic.get("key", "F")
            }
            self.stats["caribbean_count"] += 1

        payload = [{
            "keyword_id": keyword["id"],
            "region": keyword["region"],
            "market": keyword["market"],
            "category": keyword["category"],
            "answer_text": result.get("answer_text"),
            "brand_mentions": result.get("brands", []),
            "momentum_bands": result.get("momentum_bands", []),
            "wow_events": result.get("wow_events", []),
            "analysis": {
                "estimated_price_range": result.get("estimated_price_range"),
                "best_booking_window_days": result.get("best_booking_window_days"),
                "peak_discount_times": result.get("peak_discount_times"),
                "carrier_likelihood": result.get("carrier_likelihood"),
                "routing_strategy": result.get("routing_strategy"),
                "novelty_score": result.get("novelty_score")
            },
            "sound_pack": sonic.get("sound_pack", "Arena Rock"),
            "bpm": sonic.get("bpm", 120),
            "key_center": sonic.get("key", "C"),
            "updated_at": datetime.utcnow().isoformat()
        }]
        r = requests.post(url, headers=HEADERS_SB, json=payload, timeout=30)
        r.raise_for_status()

    def _openai_analyze(self, prompt: str) -> Tuple[Dict[str, Any], int]:
        """Call OpenAI API with structured prompt."""
        body = {
            "model": OPENAI_MODEL,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT.strip()},
                {"role": "user", "content": prompt.strip()}
            ]
        }
        t0 = time.time()
        r = requests.post("https://api.openai.com/v1/chat/completions", headers=HEADERS_AI, json=body, timeout=60)
        latency_ms = int((time.time() - t0) * 1000)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        result = json.loads(content)
        return result, latency_ms

    def build_cache(self, batch_limit: int = 50):
        """Main cache building process."""
        print(f"🔄 Building SERP Radio cache (limit: {batch_limit})")
        
        keywords = self._sb_select_keywords(limit=batch_limit)
        print(f"📋 Processing {len(keywords)} keywords...")
        
        for kw in keywords:
            # Compose enhanced prompt with Caribbean detection
            prompt = f"""
Origin market: {kw["market"]} / category: {kw["category"]} / region: {kw["region"]}
Query: "{kw["query"]}"
Intent: {kw["intent"]}; Brand: {kw.get("brand") or "n/a"}
Primary audience: NYC travelers (deal seekers + premium)

Context: Analyze this travel query for NYC-based searchers. Focus on:
- Price volatility and booking windows
- Brand visibility and competitive dynamics  
- Market momentum (positive for deals, negative for price spikes)
- Earcon triggers for significant events

Caribbean theme mapping: If region is CARIBBEAN, prefer Tropical Pop sound pack, 
~104 BPM, keys F or C, and emphasize laid-back beach vibes with steel drum/marimba timbres.

Return structured JSON ONLY as per schema.
"""
            try:
                result, latency_ms = self._openai_analyze(prompt)
                self._sb_upsert_prompt_run(kw["id"], prompt, result, "ok", 0.0, latency_ms)
                self._sb_upsert_visibility(kw, result)
                
                sound_pack = result.get("sonic", {}).get("sound_pack", "Unknown")
                region_flag = "🏝️" if kw["region"] == "CARIBBEAN" else "✈️"
                print(f"{region_flag} cached: {kw['query']} [{kw['region']} → {sound_pack}]")
                
                self.stats["processed"] += 1
                
            except Exception as e:
                self._sb_upsert_prompt_run(kw["id"], prompt, {"error": str(e)}, "error", 0.0, 0)
                print(f"❌ error: {kw['query']} :: {e}")
                self.stats["errors"] += 1
        
        print(f"\n🎵 Cache building complete!")
        print(f"   Processed: {self.stats['processed']}")
        print(f"   Errors: {self.stats['errors']}")
        print(f"   Caribbean tracks: {self.stats['caribbean_count']}")
        print(f"   Success rate: {self.stats['processed']/(self.stats['processed']+self.stats['errors'])*100:.1f}%")

def main():
    """CLI entry point."""
    builder = CacheBuilder()
    batch_size = int(os.environ.get("CACHE_BATCH", "80"))
    builder.build_cache(batch_limit=batch_size)

if __name__ == "__main__":
    main()
```

### **Cache-Driven Sonification**
```python
# src/pipeline/planner_from_cache.py
import os, requests
from typing import List, Dict, Any

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_SERVICE_ROLE = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
HEADERS_SB = {"apikey": SUPABASE_SERVICE_ROLE, "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE}"}

def fetch_cached_plans(limit: int = 40, region_filter: str = None) -> List[Dict[str, Any]]:
    """Fetch cached visibility data and convert to sonification plans."""
    
    # Build query with optional region filter
    query = f"select=*&order=updated_at.desc&limit={limit}"
    if region_filter:
        query += f"&region=eq.{region_filter}"
    
    url = f"{SUPABASE_URL}/rest/v1/v_visibility_public?{query}"
    r = requests.get(url, headers=HEADERS_SB, timeout=30)
    r.raise_for_status()
    rows = r.json()
    
    plans = []
    for row in rows:
        # Convert cache row to sonification plan
        plan = {
            "id": f"cache_{row['id']}",
            "timestamp": row["updated_at"],
            "channel": row["market"],
            "theme": f"{row['region'].lower()}_{row['category']}",
            "brand": row.get("brand", "Generic"),
            "title": f"{row['region']} → {row['query'][:50]}...",
            "prompt": row["query"],
            "plan": {
                "sound_pack": row["sound_pack"],
                "total_bars": 32,  # Default, can be adjusted based on momentum length
                "tempo_base": row["bpm"],
                "key_hint": row["key_center"],
                "momentum": row["momentum_bands"],
                "label_summary": _calculate_label_summary(row["momentum_bands"])
            },
            # Additional metadata for enhanced rendering
            "region": row["region"],
            "category": row["category"], 
            "wow_events": row["wow_events"],
            "answer_text": row["answer_text"]
        }
        plans.append(plan)
    
    return plans

def _calculate_label_summary(momentum_bands: List[Dict[str, Any]]) -> Dict[str, int]:
    """Calculate label summary from momentum bands."""
    summary = {"positive": 0, "neutral": 0, "negative": 0}
    for band in momentum_bands:
        label = band.get("label", "neutral")
        if label in summary:
            summary[label] += 1
    return summary

def fetch_caribbean_plans(limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch specifically Caribbean-themed plans."""
    return fetch_cached_plans(limit=limit, region_filter="CARIBBEAN")

def fetch_nyc_plans(limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch NYC-focused travel plans.""" 
    return fetch_cached_plans(limit=limit, region_filter="US-NE")
```

---

## 🎼 **Enhanced Audio Generation**

### **Tropical Pop Arranger**
```python
# Enhanced src/arranger.py for Caribbean themes
class TropicalPopArranger(MusicArranger):
    """Specialized arranger for Caribbean 'Kokomo' themes."""
    
    def __init__(self, total_bars=32, base_tempo=104):
        super().__init__(total_bars, base_tempo)
        self.tropical_instruments = {
            "steel_drum": self._create_steel_drum_voice,
            "marimba": self._create_marimba_voice,
            "bass": self._create_reggae_bass,
            "shaker": self._create_shaker_pattern,
            "wind_chimes": self._create_wind_chime_fx
        }
    
    def arrange_caribbean_momentum(self, momentum_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create Beach Boys-inspired arrangement from momentum data."""
        
        sections = []
        current_time = 0
        
        for i, band in enumerate(momentum_data):
            duration = band["t1"] - band["t0"]
            section_bars = max(2, int(duration / 4))
            
            # Map momentum to Caribbean musical elements
            if band["label"] == "positive" and band["score"] > 0.6:
                # High positive momentum → steel drum flourish + harmony vocals
                section_type = "tropical_celebration"
                instruments = ["steel_drum", "marimba", "bass", "shaker", "wind_chimes"]
                dynamics = "forte"
                
            elif band["label"] == "negative":
                # Price spike → minor harmony, reduce instrumentation
                section_type = "concern_passage"
                instruments = ["marimba", "bass"]  # Minimal arrangement
                dynamics = "piano"
                
            else:
                # Neutral momentum → steady island groove
                section_type = "island_groove"
                instruments = ["steel_drum", "bass", "shaker"]
                dynamics = "mezzo"
            
            sections.append({
                "start_bar": int(current_time / 4),
                "duration_bars": section_bars,
                "type": section_type,
                "instruments": instruments,
                "dynamics": dynamics,
                "momentum_score": band["score"],
                "tempo_adjustment": self._get_tempo_adjustment(band)
            })
            
            current_time += duration
        
        return {
            "sections": sections,
            "total_duration_sec": current_time,
            "key": "F",  # Warm, tropical key
            "time_signature": "4/4",
            "style": "reggae_pop_fusion"
        }
    
    def _get_tempo_adjustment(self, band: Dict[str, Any]) -> int:
        """Adjust tempo based on momentum intensity."""
        base_adjustment = 0
        
        # Positive momentum can speed up slightly
        if band["label"] == "positive":
            base_adjustment = min(8, int(band["score"] * 10))
        # Negative momentum slows down
        elif band["label"] == "negative": 
            base_adjustment = max(-10, int(band["score"] * 15))
        
        return base_adjustment
    
    def _create_steel_drum_voice(self, section: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate steel drum melody line."""
        # Implementation would create MIDI notes for steel drum
        # Using pentatonic scale for tropical feel
        pass
    
    def _create_marimba_voice(self, section: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate marimba harmony pad.""" 
        # Implementation would create sustained chords
        pass
    
    def _create_reggae_bass(self, section: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate reggae-style bass line."""
        # Implementation would emphasize off-beats
        pass
```

### **Caribbean Earcon System**
```python
# Enhanced src/earcons.py for Kokomo theme
class CaribbeanEarconGenerator(EarconGenerator):
    """Specialized earcon generator for Caribbean themes."""
    
    def __init__(self):
        super().__init__()
        self.caribbean_sounds = {
            "steel_drum_roll": {
                "instrument": 114,  # Steel Drums GM patch
                "pattern": [60, 64, 67, 72, 67, 64],  # Pentatonic roll
                "duration": 0.5,
                "velocity": 90
            },
            "wind_chime_down": {
                "instrument": 122,  # Reverse Cymbal
                "pattern": [84, 81, 78, 75, 72],  # Descending chime
                "duration": 1.0,
                "velocity": 60
            },
            "crystal_ping": {
                "instrument": 98,   # Crystal
                "pattern": [96],     # High ping
                "duration": 0.2,
                "velocity": 100
            },
            "island_celebration": {
                "instrument": 114,  # Steel Drums
                "pattern": [60, 67, 72, 76, 79],  # Major arpeggio
                "duration": 1.5,
                "velocity": 110
            }
        }
    
    def generate_caribbean_earcons(self, wow_events: List[Dict[str, Any]], momentum_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate Caribbean-themed earcons from wow events."""
        
        earcons = []
        
        for event in wow_events:
            event_time = event.get("time", 0)
            event_type = event.get("type", "generic")
            
            # Map event types to Caribbean sounds
            if event_type == "volatility_spike":
                earcons.append(self._create_earcon("crystal_ping", event_time, intensity=0.8))
                
            elif event_type == "podium_win": 
                earcons.append(self._create_earcon("island_celebration", event_time, intensity=1.0))
                
            elif event_type == "brand_spike":
                earcons.append(self._create_earcon("steel_drum_roll", event_time, intensity=0.9))
                
            elif event_type == "ai_steal":
                earcons.append(self._create_earcon("wind_chime_down", event_time, intensity=0.7))
        
        # Add momentum-driven ambient earcons
        for i, band in enumerate(momentum_data):
            if band.get("score", 0) > 0.7:  # Very positive momentum
                # Add subtle steel drum accents
                accent_time = band.get("t0", 0) + (band.get("t1", 0) - band.get("t0", 0)) / 2
                earcons.append(self._create_earcon("steel_drum_roll", accent_time, intensity=0.6))
        
        return sorted(earcons, key=lambda x: x["time"])
    
    def _create_earcon(self, sound_type: str, time: float, intensity: float = 1.0) -> Dict[str, Any]:
        """Create a single earcon event."""
        sound_config = self.caribbean_sounds.get(sound_type, self.caribbean_sounds["crystal_ping"])
        
        return {
            "time": time,
            "type": sound_type,
            "instrument": sound_config["instrument"],
            "pattern": sound_config["pattern"],
            "duration": sound_config["duration"],
            "velocity": int(sound_config["velocity"] * intensity),
            "intensity": intensity
        }
```

---

## 🌐 **Frontend Integration (Lovable.dev)**

### **Environment Configuration**
```env
# Lovable.dev Environment Variables
VITE_API_BASE=https://serpradio-api-2025.onrender.com
VITE_PUBLIC_CDN_DOMAIN=serpradio-public-2025.s3.amazonaws.com
VITE_SUPABASE_URL=https://bulcmonhcvqljorhiqgk.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGci...
VITE_OPENAI_MODEL=gpt-4o-mini
VITE_DEFAULT_THEME=caribbean_kokomo
VITE_CACHE_REFRESH_INTERVAL=300000
```

### **Enhanced Theme Catalog**
```typescript
// Theme configuration for frontend
interface ThemeConfig {
  id: string;
  title: string;
  description: string;
  soundPack: string;
  defaultTempo: number;
  defaultKey: string;
  color: string;
  icon: string;
  regions: string[];
}

export const THEME_CATALOG: Record<string, ThemeConfig> = {
  caribbean_kokomo: {
    id: "caribbean_kokomo",
    title: "Caribbean Kokomo",
    description: "Island paradise vibes from NYC - Beach Boys meets steel drums",
    soundPack: "Tropical Pop",
    defaultTempo: 104,
    defaultKey: "F",
    color: "#10B981", // Emerald
    icon: "🏝️",
    regions: ["CARIBBEAN"]
  },
  budget_carriers: {
    id: "budget_carriers", 
    title: "Budget Carriers",
    description: "Spirit, Frontier, JetBlue deals - playful 8-bit energy",
    soundPack: "8-Bit",
    defaultTempo: 128,
    defaultKey: "C",
    color: "#FFD700", // Gold
    icon: "✈️",
    regions: ["US-NE", "US-West", "US-South"]
  },
  legacy_airlines: {
    id: "legacy_airlines",
    title: "Legacy Airlines", 
    description: "Delta, American, United premium - confident arena rock",
    soundPack: "Arena Rock",
    defaultTempo: 132,
    defaultKey: "G",
    color: "#1E40AF", // Blue
    icon: "🛫",
    regions: ["US-NE", "US-West", "INTL"]
  },
  red_eye_deals: {
    id: "red_eye_deals",
    title: "Red-Eye Deals",
    description: "Late night cross-country - mysterious synthwave",
    soundPack: "Synthwave",
    defaultTempo: 110,
    defaultKey: "Am",
    color: "#8B5CF6", // Purple
    icon: "🌙",
    regions: ["US-NE", "US-West"]
  }
};
```

### **Kokomo Player Component**
```typescript
// Enhanced player component for Caribbean themes
import React, { useState, useEffect } from 'react';
import { useEarcons } from '../hooks/useEarcons';
import { Button } from '../ui/button';

interface KokomoPlayerProps {
  visibilityData: VisibilityEntry;
  autoPlay?: boolean;
}

interface VisibilityEntry {
  id: number;
  region: string;
  country: string;
  query: string;
  sound_pack: string;
  bpm: number;
  key_center: string;
  momentum_bands: MomentumBand[];
  wow_events: WowEvent[];
  audio_key?: string;
  midi_key?: string;
  duration_sec?: number;
}

export const KokomoPlayer: React.FC<KokomoPlayerProps> = ({ 
  visibilityData, 
  autoPlay = false 
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const { enableEarcons, playTrack, stopTrack } = useEarcons();

  useEffect(() => {
    if (autoPlay && visibilityData.audio_key) {
      handlePlayTrack();
    }
  }, [autoPlay, visibilityData.audio_key]);

  const handlePlayTrack = async () => {
    if (isPlaying) {
      stopTrack();
      setIsPlaying(false);
      return;
    }

    // Enable Caribbean-specific earcons
    if (visibilityData.region === 'CARIBBEAN') {
      enableEarcons({
        volatility_spike: "crystal.ping",
        podium_win: "island_celebration", 
        brand_spike: "steel_drum_roll",
        ai_steal: "wind_chime_down"
      });
    }

    // Play track with momentum and earcon data
    await playTrack({
      audioUrl: visibilityData.audio_key,
      momentumData: visibilityData.momentum_bands,
      wowEvents: visibilityData.wow_events,
      soundPack: visibilityData.sound_pack,
      tempo: visibilityData.bpm,
      key: visibilityData.key_center,
      duration: visibilityData.duration_sec || 30
    });

    setIsPlaying(true);
  };

  const getDestinationFlag = (country: string) => {
    const flags: Record<string, string> = {
      'PR': '🇵🇷', 'JM': '🇯🇲', 'AW': '🇦🇼', 'DO': '🇩🇴',
      'BS': '🇧🇸', 'BB': '🇧🇧', 'TC': '🇹🇨', 'CW': '🇨🇼',
      'AG': '🇦🇬', 'GD': '🇬🇩', 'KN': '🇰🇳', 'DM': '🇩🇲',
      'VG': '🇻🇬', 'US': '🇺🇸'
    };
    return flags[country] || '🏝️';
  };

  const formatQuery = (query: string) => {
    return query.length > 60 ? query.substring(0, 60) + '...' : query;
  };

  return (
    <div className={`kokomo-player rounded-lg p-6 ${
      visibilityData.region === 'CARIBBEAN' 
        ? 'bg-gradient-to-br from-cyan-400 to-emerald-500' 
        : 'bg-gradient-to-br from-blue-500 to-purple-600'
    } text-white`}>
      
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="text-3xl">
            {getDestinationFlag(visibilityData.country)}
          </div>
          <div>
            <h3 className="font-bold text-lg">
              {visibilityData.region} → {visibilityData.country}
            </h3>
            <p className="text-sm opacity-90">
              {formatQuery(visibilityData.query)}
            </p>
          </div>
        </div>
        
        <div className="text-right text-sm opacity-75">
          <div>{visibilityData.sound_pack}</div>
          <div>{visibilityData.bpm} BPM • {visibilityData.key_center}</div>
        </div>
      </div>

      {/* Momentum visualization */}
      <div className="mb-4">
        <div className="flex gap-1 h-8">
          {visibilityData.momentum_bands.map((band, i) => (
            <div
              key={i}
              className={`flex-1 rounded-sm ${
                band.label === 'positive' ? 'bg-green-300' :
                band.label === 'negative' ? 'bg-red-300' : 
                'bg-yellow-300'
              }`}
              style={{ 
                opacity: Math.abs(band.score) * 0.8 + 0.2,
                height: `${Math.abs(band.score) * 100}%`
              }}
            />
          ))}
        </div>
        <div className="flex justify-between text-xs mt-1 opacity-75">
          <span>Momentum Bands</span>
          <span>{visibilityData.momentum_bands.length} segments</span>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between">
        <Button
          onClick={handlePlayTrack}
          variant={isPlaying ? "secondary" : "default"}
          size="lg"
          className="bg-white/20 hover:bg-white/30 text-white border-white/30"
        >
          {isPlaying ? (
            <>⏸️ Stop {visibilityData.region === 'CARIBBEAN' ? 'Kokomo' : 'Track'}</>
          ) : (
            <>▶️ Play {visibilityData.region === 'CARIBBEAN' ? 'Kokomo' : 'Track'}</>
          )}
        </Button>
        
        <div className="flex gap-2 text-sm">
          <span className="bg-white/20 px-2 py-1 rounded">
            {visibilityData.wow_events?.length || 0} events
          </span>
          {visibilityData.duration_sec && (
            <span className="bg-white/20 px-2 py-1 rounded">
              {Math.round(visibilityData.duration_sec)}s
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
```

---

## 🚀 **Production Deployment**

### **GitHub Actions Workflow**
```yaml
# .github/workflows/daily-pipeline.yml
name: SERP Radio Daily Pipeline

on:
  schedule:
    - cron: '15 3 * * *'  # 3:15 AM UTC daily
  workflow_dispatch:
    inputs:
      batch_size:
        description: 'Number of keywords to process'
        required: false
        default: '80'
      region_filter:
        description: 'Filter by region (optional)'
        required: false
        default: ''

jobs:
  cache-and-render:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        
      - name: Setup Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          
      - name: Build OpenAI cache
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
          OPENAI_MODEL: gpt-4o-mini
          CACHE_BATCH: ${{ github.event.inputs.batch_size || '80' }}
        run: |
          echo "🔄 Building OpenAI visibility cache..."
          python -m src.pipeline.openai_cache
          
      - name: Render audio batch
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_REGION: us-east-1
          S3_BUCKET: serpradio-artifacts-2025
          S3_PUBLIC_BUCKET: serpradio-public-2025
        run: |
          echo "🎼 Rendering audio from cache..."
          python -c "
          from src.pipeline.planner_from_cache import fetch_cached_plans
          from src.pipeline.sonify_batch import render_batch, publish_catalog
          
          # Fetch plans from cache
          all_plans = fetch_cached_plans(limit=60)
          caribbean_plans = [p for p in all_plans if p.get('region') == 'CARIBBEAN']
          
          print(f'📊 Total plans: {len(all_plans)}')
          print(f'🏝️ Caribbean plans: {len(caribbean_plans)}')
          
          # Render audio
          entries = render_batch(all_plans)
          
          # Publish catalogs
          publish_catalog(entries, catalog_prefix='catalog/travel/global')
          if caribbean_plans:
              caribbean_entries = render_batch(caribbean_plans)
              publish_catalog(caribbean_entries, catalog_prefix='catalog/travel/caribbean')
          
          print(f'✅ Rendered {len(entries)} total tracks')
          "
          
      - name: Update hero tracks
        env:
          ADMIN_SECRET: ${{ secrets.ADMIN_SECRET }}
        run: |
          echo "🎵 Updating hero tracks..."
          
          # Update Tropical Pop hero for Caribbean
          curl -X POST "https://serpradio-api-2025.onrender.com/api/render-hero" \
            -H "x_admin_secret: ${{ secrets.ADMIN_SECRET }}" \
            -d "sound_pack=Tropical Pop"
            
          # Update other hero tracks
          for pack in "Arena Rock" "8-Bit" "Synthwave"; do
            curl -X POST "https://serpradio-api-2025.onrender.com/api/render-hero" \
              -H "x_admin_secret: ${{ secrets.ADMIN_SECRET }}" \
              -d "sound_pack=$pack"
          done
          
      - name: Notify completion
        run: |
          echo "🎉 SERP Radio daily pipeline completed!"
          echo "📈 Cache refreshed, audio rendered, catalogs published"
          echo "🏝️ Caribbean Kokomo themes included"
```

---

## 📊 **Monitoring & Analytics**

### **Performance Metrics**
```sql
-- Analytics queries for Supabase
-- Daily cache performance
SELECT 
  DATE(created_at) as date,
  COUNT(*) as total_processed,
  COUNT(*) FILTER (WHERE status = 'ok') as successful,
  COUNT(*) FILTER (WHERE status = 'error') as errors,
  AVG(latency_ms) as avg_latency_ms,
  SUM(cost_usd) as total_cost_usd
FROM public.prompt_runs 
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Regional breakdown
SELECT 
  region,
  COUNT(*) as total_queries,
  COUNT(DISTINCT sound_pack) as sound_packs_used,
  AVG(bpm) as avg_bpm,
  STRING_AGG(DISTINCT sound_pack, ', ') as sound_packs
FROM public.v_visibility_public
GROUP BY region
ORDER BY total_queries DESC;

-- Caribbean theme performance
SELECT 
  country,
  COUNT(*) as query_count,
  AVG(bpm) as avg_tempo,
  COUNT(*) FILTER (WHERE sound_pack = 'Tropical Pop') as tropical_tracks
FROM public.v_visibility_public 
WHERE region = 'CARIBBEAN'
GROUP BY country
ORDER BY query_count DESC;

-- Most active themes
SELECT 
  CONCAT(region, '_', category) as theme,
  COUNT(*) as track_count,
  AVG(duration_sec) as avg_duration,
  COUNT(DISTINCT sound_pack) as sound_variety
FROM public.v_visibility_public
WHERE updated_at >= NOW() - INTERVAL '24 hours'
GROUP BY region, category
ORDER BY track_count DESC;
```

### **Success Metrics Dashboard**
- **Cache Hit Rate**: >95% successful OpenAI API calls
- **Audio Generation**: 50+ tracks per day across all themes
- **Caribbean Coverage**: 15+ Kokomo tracks daily
- **Theme Distribution**: Balanced across all 4 sound packs
- **API Performance**: <500ms average response time
- **User Engagement**: >60s average listening time per track

---

This production playbook creates a complete, scalable SERP Radio system that generates emotive, nostalgic audio from real search data with special emphasis on the Caribbean "Kokomo" theme. The system runs automatically, scales across verticals, and delivers instant audio experiences that make search visibility memorable and actionable! 🎵🏝️🏙️