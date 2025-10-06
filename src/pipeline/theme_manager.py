"""
Multi-theme pipeline manager for scalable vertical expansion.
"""
import os
import yaml
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from .schemas import LLMFlightResult, SonifyPlan, MomentumBand
from .openai_client import FlightLLM
from .nostalgia import brand_to_sound_pack, routing_to_energy

class ThemeManager:
    """Manages multiple themes within verticals for scalable content generation."""
    
    def __init__(self, base_path: str = "src/pipeline/prompt_library"):
        self.base_path = Path(base_path)
        self.themes: Dict[str, Dict[str, Any]] = {}
        self.load_themes()
    
    def load_themes(self) -> None:
        """Load all available themes from YAML files."""
        for vertical_dir in self.base_path.iterdir():
            if vertical_dir.is_dir():
                vertical_name = vertical_dir.name
                self.themes[vertical_name] = {}
                
                # Load vertical-level themes
                for theme_file in vertical_dir.glob("*.yaml"):
                    theme_name = theme_file.stem
                    with open(theme_file, 'r') as f:
                        theme_config = yaml.safe_load(f)
                    self.themes[vertical_name][theme_name] = theme_config
                
                # Load sub-theme directories
                for theme_dir in vertical_dir.iterdir():
                    if theme_dir.is_dir():
                        theme_name = theme_dir.name
                        self.themes[vertical_name][theme_name] = {}
                        
                        for sub_theme_file in theme_dir.glob("*.yaml"):
                            sub_theme_name = sub_theme_file.stem
                            with open(sub_theme_file, 'r') as f:
                                sub_theme_config = yaml.safe_load(f)
                            self.themes[vertical_name][theme_name][sub_theme_name] = sub_theme_config
    
    def get_available_themes(self, vertical: str = None) -> Dict[str, Any]:
        """Get all available themes, optionally filtered by vertical."""
        if vertical:
            return self.themes.get(vertical, {})
        return self.themes
    
    def get_theme_config(self, vertical: str, theme: str, sub_theme: str = None) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific theme."""
        try:
            if sub_theme:
                return self.themes[vertical][theme][sub_theme]
            else:
                return self.themes[vertical][theme]
        except KeyError:
            return None
    
    def build_prompts_for_theme(self, vertical: str, theme: str, sub_theme: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Build prompts for a specific theme with enhanced granularity."""
        config = self.get_theme_config(vertical, theme, sub_theme)
        if not config:
            raise ValueError(f"Theme not found: {vertical}/{theme}/{sub_theme or ''}")
        
        origins = config.get("origins", [])
        destinations = config.get("destinations", [])
        templates = config.get("templates", [])
        novelty_special = config.get("novelty_special", [])
        
        prompts = []
        
        # Regular origin-destination combinations
        for origin in origins:
            for dest_info in destinations:
                dest_code = dest_info["code"] if isinstance(dest_info, dict) else dest_info
                dest_name = dest_info.get("name", dest_code) if isinstance(dest_info, dict) else dest_code
                
                for template in templates:
                    prompts.append({
                        "origin": origin,
                        "destination": dest_code,
                        "title": f"{origin}->{dest_code} ({sub_theme or theme})",
                        "prompt": template.format(origin=origin, dest=dest_name),
                        "theme": theme,
                        "sub_theme": sub_theme,
                        "sound_pack_hint": config.get("sound_pack_default", "Synthwave")
                    })
        
        # Add novelty/special prompts
        for special in novelty_special:
            prompts.append({
                "origin": "NYC_ALL",
                "destination": "MULTI",
                "title": f"NYC SPECIAL ({sub_theme or theme})",
                "prompt": special,
                "theme": theme,
                "sub_theme": sub_theme,
                "sound_pack_hint": config.get("sound_pack_default", "Synthwave")
            })
        
        # Limit results
        if limit:
            prompts = prompts[:limit]
        
        return prompts
    
    def enhanced_nostalgia_mapping(self, config: Dict[str, Any], llm_result: LLMFlightResult) -> str:
        """Enhanced sound pack selection based on theme configuration."""
        # Start with theme default
        sound_pack = config.get("sound_pack_default", "Synthwave")
        
        # Check carrier-specific mappings
        carriers = config.get("carriers", [])
        if llm_result.carrier_likelihood:
            primary_carrier = llm_result.carrier_likelihood[0].lower()
            for carrier_info in carriers:
                if isinstance(carrier_info, dict):
                    carrier_name = carrier_info.get("name", "").lower()
                    if carrier_name in primary_carrier:
                        sound_pack = carrier_info.get("sound_pack", sound_pack)
                        break
        
        # Caribbean destinations → Tropical Pop
        if config.get("sub_theme") == "caribbean_kokomo":
            sound_pack = "Tropical Pop"
        
        # Time-based overrides for red-eye themes
        elif config.get("sub_theme") == "red_eye_deals":
            sound_pack = "Synthwave"  # Always synthwave for red-eyes
        elif config.get("sub_theme") == "ski_season":
            sound_pack = "Arena Rock"

        # Non-brand SEO and hacks → playful 8-Bit
        elif config.get("sub_theme") in ("non_brand_seo", "hidden_city_hacks"):
            sound_pack = "8-Bit"

        # Best time to book → calmer Synthwave
        elif config.get("sub_theme") == "best_time_to_book":
            sound_pack = "Synthwave"

        # Weekend getaways → Tropical Pop
        elif config.get("sub_theme") == "weekend_getaways":
            sound_pack = "Tropical Pop"
        
        # Mood-based adjustments
        mood = config.get("mood", "")
        if "tropical" in mood or "laid-back" in mood:
            sound_pack = "Tropical Pop"
        elif "budget" in mood or "frugal" in mood:
            sound_pack = "8-Bit"
        elif "premium" in mood or "business" in mood:
            sound_pack = "Arena Rock"
        elif "nocturnal" in mood or "mysterious" in mood:
            sound_pack = "Synthwave"
        
        return sound_pack
    
    def build_enhanced_plans(self, vertical: str, theme: str, sub_theme: str = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Build enhanced sonification plans with theme-aware features."""
        config = self.get_theme_config(vertical, theme, sub_theme)
        if not config:
            raise ValueError(f"Theme not found: {vertical}/{theme}/{sub_theme or ''}")
        
        prompts = self.build_prompts_for_theme(vertical, theme, sub_theme, limit)
        
        llm = FlightLLM()
        plans = []
        
        for p in prompts:
            # Get LLM analysis
            data = llm.analyze_prompt(p["prompt"])
            r = LLMFlightResult(
                origin=p["origin"], 
                destination=p["destination"], 
                prompt=p["prompt"], 
                **data
            )
            
            # Generate momentum bands
            segs = self._bands_from_llm(r, config)
            label_summary = self._label_summary(segs)
            
            # Enhanced sound pack selection
            sound_pack = self.enhanced_nostalgia_mapping(config, r)
            
            # Theme-aware tempo and bars
            tempo, bars = self._theme_aware_energy(config, r)
            
            plan = SonifyPlan(
                sound_pack=sound_pack,
                total_bars=bars,
                tempo_base=tempo,
                key_hint=None,
                momentum=segs,
                label_summary=label_summary
            )
            
            plans.append({
                "id": f"{vertical}_{theme}_{sub_theme or 'base'}_{len(plans)}",
                "timestamp": datetime.utcnow().isoformat(),
                "channel": vertical,
                "theme": theme,
                "sub_theme": sub_theme,
                "origin": p["origin"],
                "destination": p["destination"],
                "brand": r.carrier_likelihood[0] if r.carrier_likelihood else p.get("sound_pack_hint", ""),
                "title": p["title"],
                "prompt": p["prompt"],
                "plan": plan.model_dump()
            })
        
        return plans
    
    def _bands_from_llm(self, r: LLMFlightResult, config: Dict[str, Any]) -> List[MomentumBand]:
        """Generate momentum bands with theme-specific adjustments."""
        # Base implementation from travel_pipeline.py
        price_mid = None
        if r.estimated_price_range and len(r.estimated_price_range)==2:
            price_mid = (r.estimated_price_range[0] + r.estimated_price_range[1]) / 2.0

        base = self._score_from_price(price_mid)
        novelty = (r.novelty_score or 5)/10.0
        
        # Theme-specific adjustments
        mood = config.get("mood", "")
        if "budget" in mood:
            base += 0.2  # Budget deals are more positive
        elif "premium" in mood:
            base -= 0.1  # Premium is expected, less exciting
        
        segs: List[MomentumBand] = []
        t = 0.0
        segment_count = 8 if "red_eye" in config.get("sub_theme", "") else 10
        
        for i in range(segment_count):
            jitter = (novelty - 0.5) * 0.4
            score = max(-1.0, min(1.0, base + (i-4)*0.03 + jitter))
            label = "positive" if score > 0.15 else "negative" if score < -0.15 else "neutral"
            segs.append(MomentumBand(t0=t, t1=t+3.2, label=label, score=round(score, 3)))
            t += 3.2
        
        return segs
    
    def _score_from_price(self, midpoint: float) -> float:
        """Convert price to momentum score (cheaper = more positive)."""
        if midpoint is None:
            return 0.0
        a, b = 50.0, 400.0
        x = max(min(midpoint, b), a)
        norm = 1 - (x - a) / (b - a)
        return max(-1.0, min(1.0, (norm - 0.5) * 2.0))
    
    def _label_summary(self, segs: List[MomentumBand]) -> Dict[str, int]:
        """Count labels in momentum bands."""
        s = {"positive": 0, "neutral": 0, "negative": 0}
        for b in segs:
            s[b.label] += 1
        return s
    
    def _theme_aware_energy(self, config: Dict[str, Any], r: LLMFlightResult) -> tuple[int, int]:
        """Determine tempo and bars based on theme and routing."""
        base_tempo, base_bars = routing_to_energy(r.routing_strategy or "direct")
        
        # Theme-specific adjustments
        sub_theme = config.get("sub_theme", "")
        if sub_theme == "caribbean_kokomo":
            base_tempo = 104  # Laid-back beach tempo
            base_bars = max(28, base_bars - 2)     # Relaxed, moderate length
        elif sub_theme == "red_eye_deals":
            base_tempo = max(90, base_tempo - 20)  # Slower, more ambient
            base_bars = min(24, base_bars - 4)     # Shorter tracks
        elif sub_theme == "ski_season":
            base_tempo = max(110, base_tempo)
            base_bars = max(32, base_bars)
        elif sub_theme == "non_brand_seo":
            base_tempo = min(136, max(100, base_tempo))
        elif sub_theme == "best_time_to_book":
            base_tempo = max(96, base_tempo - 8)
            base_bars = max(24, base_bars)
        elif sub_theme == "hidden_city_hacks":
            base_tempo = min(140, base_tempo + 6)
        elif sub_theme == "weekend_getaways":
            base_tempo = 110
            base_bars = max(28, base_bars)
        elif sub_theme == "budget_carriers":
            base_tempo = min(140, base_tempo + 10) # Slightly faster, more energetic
        elif sub_theme == "legacy_airlines":
            base_tempo = max(100, base_tempo - 5)  # Slightly more stately
            base_bars = max(32, base_bars + 4)     # Longer, more developed
        
        return base_tempo, base_bars