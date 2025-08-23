# 🎵 SERP Radio - Complete Sonification Engine Documentation

## 🏗️ **System Overview**

SERP Radio transforms real-world search data into emotive, nostalgic audio experiences through a sophisticated **OpenAI → Momentum → Audio** pipeline with Supabase storage and multi-vertical theme support.

---

## 📡 **MCP Server Integration Context**

### **Model Context Protocol (MCP) Integration Points**

#### **1. Claude Code Server**
```typescript
// MCP Server Configuration
{
  "mcpServers": {
    "serpradio": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-filesystem", "/Users/James/Documents/tg"],
      "env": {
        "OPENAI_API_KEY": "...",
        "SUPABASE_URL": "...",
        "SUPABASE_ANON_KEY": "..."
      }
    }
  }
}
```

#### **2. Context-Aware Pipeline Triggers**
- **File System Access**: Read CSV data, YAML configs, generated audio
- **Database Operations**: Query/update Supabase via unified storage interface
- **Real-time Generation**: Trigger pipeline runs based on data freshness
- **Multi-Modal Output**: Generate audio, JSON catalogs, and visual metadata

#### **3. Agent Handoff Patterns**
```python
# MCP-aware pipeline execution
class MCPSonificationAgent:
    def __init__(self, mcp_context):
        self.context = mcp_context
        self.theme_manager = ThemeManager()
        
    async def process_request(self, vertical: str, theme: str):
        # Access CSV data via MCP filesystem
        data = await self.context.read_file(f"data/{vertical}_{theme}.csv")
        
        # Generate sonification plans
        plans = self.theme_manager.build_enhanced_plans(vertical, theme)
        
        # Store results via MCP database access
        await self.context.store_results(plans)
```

---

## 🏢 **Multi-Vertical Architecture**

### **Scalable Vertical Structure**
```
src/pipeline/
├── verticals/
│   ├── travel/
│   │   ├── flights_from_nyc/          # ⭐ PRIMARY FOCUS
│   │   │   ├── budget_carriers/       # Spirit, Frontier → 8-Bit
│   │   │   ├── legacy_airlines/       # Delta, American → Arena Rock
│   │   │   ├── red_eye_deals/         # Late night → Synthwave
│   │   │   └── caribbean_kokomo/      # 🆕 Caribbean islands → Tropical Pop
│   │   ├── hotels/                    # Future expansion
│   │   └── car_rentals/              # Future expansion
│   ├── finance/                       # Future: stocks, crypto
│   │   ├── wall_street_march/        # NYSE-focused themes
│   │   └── crypto_pulse/             # Bitcoin, ETH movements
│   └── ecommerce/                    # Future: product pricing
│       ├── deal_drums/               # Amazon, retail deals
│       └── brand_battles/            # Competitive pricing
├── shared/
│   ├── base_classes.py              # Common interfaces
│   ├── sound_pack_registry.py       # Sound pack definitions
│   └── nostalgia_engine.py          # Emotional mapping logic
└── prompt_library/                   # Theme-specific prompts
    ├── travel/
    │   ├── flights_from_nyc/
    │   │   ├── budget_carriers.yaml
    │   │   ├── legacy_airlines.yaml
    │   │   ├── red_eye_deals.yaml
    │   │   └── caribbean_kokomo.yaml  # 🆕 Kokomo theme
    │   └── travel.yaml               # Legacy single-theme
    └── finance/                      # Future themes
```

---

## 🎯 **Enhanced NYC Flights + Caribbean Focus**

### **Theme Hierarchy & Sound Mapping**

#### **1. Budget Carriers (8-Bit Sound Pack)**
```yaml
# budget_carriers.yaml
channel: travel
theme: flights_from_nyc
sub_theme: budget_carriers
sound_pack_default: "8-Bit"
mood: "playful, frugal, adventurous"

carriers:
  - name: "Spirit"
    personality: "ultra-budget, no-frills, yellow branding"
    price_range: [29, 89]
    sound_pack: "8-Bit"
  - name: "Frontier" 
    personality: "animal tails, family-friendly budget"
    price_range: [35, 95]
    sound_pack: "8-Bit"
  - name: "JetBlue"
    personality: "budget with perks, mint green, hipster"
    price_range: [45, 125]
    sound_pack: "Synthwave"

destinations:
  - code: LAS, name: Las Vegas, budget_appeal: "gambling, shows"
  - code: MIA, name: Miami, budget_appeal: "beaches, nightlife"
  - code: MCO, name: Orlando, budget_appeal: "Disney, family trips"
```

#### **2. Legacy Airlines (Arena Rock Sound Pack)**
```yaml
# legacy_airlines.yaml
theme: flights_from_nyc
sub_theme: legacy_airlines
sound_pack_default: "Arena Rock"
mood: "confident, established, premium"

carriers:
  - name: "Delta"
    personality: "premium, reliable, SkyClub access"
    hubs: ["ATL", "JFK"]
    sound_pack: "Arena Rock"
  - name: "American"
    personality: "traditional, flagship service"
    hubs: ["DFW", "JFK"] 
    sound_pack: "Arena Rock"
  - name: "United"
    personality: "global reach, Polaris business"
    hubs: ["EWR", "ORD"]
    sound_pack: "Arena Rock"

premium_features:
  - lie-flat seats, premium lounges, same-day changes
```

#### **3. Red-Eye Deals (Synthwave Sound Pack)**
```yaml
# red_eye_deals.yaml
theme: flights_from_nyc
sub_theme: red_eye_deals
sound_pack_default: "Synthwave"
mood: "nocturnal, mysterious, deal-hunting"

time_windows:
  - departure: "11:00 PM - 2:00 AM"
    arrival: "2:00 AM - 6:00 AM"
    savings: "20-40% vs daytime"

destinations:
  - code: LAX, red_eye_appeal: "cross-country classic"
  - code: SFO, red_eye_appeal: "tech commuter"
  - code: LAS, red_eye_appeal: "gambler special"
```

#### **4. 🆕 Caribbean Kokomo (Tropical Pop Sound Pack)**
```yaml
# caribbean_kokomo.yaml
channel: travel
theme: flights_from_nyc
sub_theme: caribbean_kokomo
focus: "JFK to Caribbean islands - Beach Boys 'Kokomo' vibes"
sound_pack_default: "Tropical Pop"
mood: "laid-back, tropical, nostalgic"
motif: "kokomo"

origins: [JFK, LGA, EWR]

destinations:
  - code: SJU, name: Puerto Rico, search_volume: 5490
  - code: AUA, name: Aruba, search_volume: 3610
  - code: SDQ, name: Dominican Republic, search_volume: 3580
  - code: MBJ, name: Jamaica, search_volume: 3560
  - code: CUN, name: Cancún, search_volume: 3040
  - code: CUR, name: Curaçao, search_volume: 860
  - code: NAS, name: Nassau, search_volume: 1240

sound_config:
  tempo_bpm: 104  # Laid-back beach tempo
  instrument_hints: ["marimba", "steel_drum", "vibes", "shaker"]
  
earcons:
  volatility_spike: "crystal.ping"
  podium_win: "bell.chime"
  brand_spike: "brass.stab"
  ai_steal: "lowtom.tapestop"

templates:
  - "Cheapest JFK → {dest} in next 60 days; include ultra-budget options"
  - "JFK to {dest}: red-eye only; find sub-$150 windows"
  - "Hidden-city JFK→{dest} plausibility; if unsafe/unreliable, mark low"
  - "Caribbean winter escape: NYC to {dest} avoiding holiday premiums"

novelty_special:
  - "Which Caribbean island has the biggest JFK fare drops in winter?"
  - "Ultra-budget NYC to Caribbean: Spirit vs JetBlue vs connecting flights"
  - "Hurricane season discounts: when do Caribbean flights get cheapest?"
```

---

## 🎵 **Sound Pack Evolution**

### **Current Sound Packs**
1. **8-Bit**: Playful, frugal, nostalgic (budget carriers)
2. **Arena Rock**: Confident, established, premium (legacy airlines)
3. **Synthwave**: Neon, mysterious, nocturnal (red-eye, international)

### **🆕 New: Tropical Pop (Caribbean Kokomo)**
```python
# soundpacks.py enhancement
TROPICAL_POP = {
    "name": "Tropical Pop",
    "description": "Beach Boys meets steel drums - laid-back Caribbean vibes",
    "instruments": {
        "lead": "steel_drum",
        "pad": "marimba",
        "bass": "upright_bass",
        "percussion": ["shaker", "vibes", "bongos"],
        "fx": ["ocean_waves", "seagulls"]
    },
    "tempo_range": [95, 115],
    "key_preferences": ["C", "G", "F", "Bb"],
    "mood": "relaxed, tropical, nostalgic",
    "earcon_bank": {
        "volatility_spike": "crystal.ping",
        "destination_reveal": "steel_drum_roll",
        "price_drop": "wind_chime_down",
        "deal_jackpot": "island_celebration"
    }
}
```

---

## 🗄️ **Supabase Database Schema**

### **Core Tables**
```sql
-- Sonification inventory (theme-ready)
CREATE TABLE sonification_inventory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    theme VARCHAR(50) NOT NULL,
    sub_theme VARCHAR(50),
    channel VARCHAR(50) NOT NULL,
    
    -- Route information
    origin VARCHAR(10) NOT NULL,
    destination VARCHAR(10) NOT NULL,
    destination_region VARCHAR(50),
    route_label VARCHAR(100),
    
    -- Search & pricing data
    monthly_searches INTEGER,
    avg_price_usd DECIMAL(8,2),
    top_keywords TEXT[],
    
    -- Sonification metadata
    sound_pack VARCHAR(50) NOT NULL,
    tempo_bpm INTEGER DEFAULT 120,
    duration_sec DECIMAL(5,2) DEFAULT 32.0,
    
    -- Audio outputs
    mp3_url TEXT,
    midi_url TEXT,
    momentum_json JSONB,
    label_summary JSONB,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_generated TIMESTAMP WITH TIME ZONE,
    
    -- Indexing
    INDEX idx_theme_subtheme (theme, sub_theme),
    INDEX idx_route (origin, destination),
    INDEX idx_region (destination_region)
);

-- Flight price data (source data)
CREATE TABLE flight_price_data (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    origin VARCHAR(10) NOT NULL,
    destination VARCHAR(10) NOT NULL,
    destination_region VARCHAR(50),
    
    -- Pricing info
    min_price_usd DECIMAL(8,2),
    max_price_usd DECIMAL(8,2),
    booking_window_days INTEGER,
    routing_strategy VARCHAR(20), -- direct, connecting, hidden-city
    
    -- LLM analysis
    novelty_score DECIMAL(3,2), -- 1-10 scale
    carrier_likelihood TEXT[],
    prompt TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Dashboard view for regional summaries
CREATE VIEW v_visibility_by_region AS
SELECT 
    destination_region,
    COUNT(*) as route_count,
    AVG(avg_price_usd) as avg_price,
    SUM(monthly_searches) as total_searches,
    ARRAY_AGG(DISTINCT sound_pack) as sound_packs_used
FROM sonification_inventory 
GROUP BY destination_region
ORDER BY total_searches DESC;
```

### **Sample Data (Caribbean Kokomo)**
```sql
-- Caribbean Kokomo theme entries
INSERT INTO sonification_inventory (
    theme, sub_theme, channel, origin, destination, destination_region,
    route_label, monthly_searches, sound_pack, tempo_bpm,
    momentum_json, label_summary
) VALUES 
(
    'flights_from_nyc', 'caribbean_kokomo', 'travel',
    'JFK', 'SJU', 'Caribbean',
    'JFK→Puerto Rico (Kokomo)', 5490, 'Tropical Pop', 104,
    '[{"t0":0,"t1":3.2,"label":"positive","score":0.7}]',
    '{"positive":6,"neutral":2,"negative":2}'
),
(
    'flights_from_nyc', 'caribbean_kokomo', 'travel', 
    'JFK', 'AUA', 'Caribbean',
    'JFK→Aruba (Kokomo)', 3610, 'Tropical Pop', 104,
    '[{"t0":0,"t1":3.2,"label":"positive","score":0.8}]',
    '{"positive":7,"neutral":2,"negative":1}'
);
```

---

## 🔄 **Enhanced Pipeline Architecture**

### **Theme Manager (Multi-Vertical Support)**
```python
# src/pipeline/theme_manager.py
class ThemeManager:
    def __init__(self, base_path="src/pipeline/prompt_library"):
        self.themes = {}
        self.load_themes()
    
    def load_themes(self):
        """Load all YAML theme configurations."""
        for vertical_dir in self.base_path.iterdir():
            vertical_name = vertical_dir.name
            self.themes[vertical_name] = {}
            
            # Load sub-theme directories
            for theme_dir in vertical_dir.iterdir():
                if theme_dir.is_dir():
                    theme_name = theme_dir.name
                    self.themes[vertical_name][theme_name] = {}
                    
                    for sub_theme_file in theme_dir.glob("*.yaml"):
                        sub_theme_name = sub_theme_file.stem
                        with open(sub_theme_file, 'r') as f:
                            config = yaml.safe_load(f)
                        self.themes[vertical_name][theme_name][sub_theme_name] = config
    
    def build_enhanced_plans(self, vertical, theme, sub_theme=None, limit=20):
        """Generate sonification plans with theme-aware features."""
        config = self.get_theme_config(vertical, theme, sub_theme)
        prompts = self.build_prompts_for_theme(vertical, theme, sub_theme, limit)
        
        llm = FlightLLM()
        plans = []
        
        for p in prompts:
            # Get OpenAI analysis
            data = llm.analyze_prompt(p["prompt"])
            result = LLMFlightResult(origin=p["origin"], destination=p["destination"], prompt=p["prompt"], **data)
            
            # Generate momentum bands
            segs = self._bands_from_llm(result, config)
            label_summary = self._label_summary(segs)
            
            # Enhanced sound pack selection
            sound_pack = self.enhanced_nostalgia_mapping(config, result)
            
            # Theme-aware tempo and bars
            tempo, bars = self._theme_aware_energy(config, result)
            
            plan = SonifyPlan(
                sound_pack=sound_pack,
                total_bars=bars,
                tempo_base=tempo,
                momentum=segs,
                label_summary=label_summary
            )
            
            plans.append({
                "id": f"{vertical}_{theme}_{sub_theme}_{len(plans)}",
                "timestamp": datetime.utcnow().isoformat(),
                "channel": vertical,
                "theme": theme,
                "sub_theme": sub_theme,
                "plan": plan.model_dump()
            })
        
        return plans

    def enhanced_nostalgia_mapping(self, config, llm_result):
        """Enhanced sound pack selection based on theme."""
        sound_pack = config.get("sound_pack_default", "Synthwave")
        
        # Caribbean destinations → Tropical Pop
        if config.get("sub_theme") == "caribbean_kokomo":
            return "Tropical Pop"
        
        # Time-based overrides
        if config.get("sub_theme") == "red_eye_deals":
            return "Synthwave"
        
        # Carrier-specific mappings
        carriers = config.get("carriers", [])
        if llm_result.carrier_likelihood:
            primary_carrier = llm_result.carrier_likelihood[0].lower()
            for carrier_info in carriers:
                if isinstance(carrier_info, dict):
                    carrier_name = carrier_info.get("name", "").lower()
                    if carrier_name in primary_carrier:
                        sound_pack = carrier_info.get("sound_pack", sound_pack)
                        break
        
        return sound_pack
```

### **Enhanced Pipeline Runner**
```bash
# scripts/run_travel_pipeline_local.sh
#!/usr/bin/env bash
set -euo pipefail

echo "🎵 SERP Radio: Enhanced Multi-Theme Pipeline"
export $(cat creds.env.txt | grep -v '^#' | xargs)

echo "🎯 Themes: Budget Carriers, Legacy Airlines, Red-Eye Deals, Caribbean Kokomo"

# Run multi-theme pipeline
python -m src.pipeline.run_pipeline \
  --vertical travel \
  --theme flights_from_nyc \
  --sub-themes budget_carriers legacy_airlines red_eye_deals caribbean_kokomo \
  --tracks-per-theme 6 \
  --limit 24

echo "🏝️ Kokomo vibes generated! Check Supabase for Caribbean audio tracks."
```

---

## 🎼 **Audio Generation & Earcons**

### **Enhanced Earcon System**
```python
# src/earcons.py enhancements
class KokomoEarconGenerator(EarconGenerator):
    def __init__(self):
        super().__init__()
        self.tropical_bank = {
            "steel_drum_roll": self._generate_steel_drum_roll,
            "crystal_ping": self._generate_crystal_ping,
            "wind_chime_down": self._generate_wind_chime,
            "island_celebration": self._generate_celebration_arp
        }
    
    def generate_caribbean_earcons(self, momentum_data, destination_code):
        """Generate Caribbean-specific earcons based on destination."""
        earcons = []
        
        for i, band in enumerate(momentum_data):
            if band["label"] == "positive" and band["score"] > 0.6:
                # High positive momentum → steel drum flourish
                earcons.append({
                    "time": band["t0"],
                    "type": "steel_drum_roll",
                    "intensity": band["score"],
                    "destination": destination_code
                })
            elif band["label"] == "negative":
                # Price spike → wind chime descending
                earcons.append({
                    "time": band["t0"],
                    "type": "wind_chime_down", 
                    "intensity": abs(band["score"])
                })
        
        return earcons
```

### **Tropical Pop Sound Pack Implementation**
```python
# src/soundpacks.py
def create_tropical_pop_arrangement(momentum_data, tempo=104):
    """Create Beach Boys-inspired tropical arrangement."""
    
    # Base rhythm: laid-back 4/4 with reggae upbeat
    rhythm_pattern = [1, 0, 0.5, 0, 1, 0, 0.5, 0]  # Emphasize beats 2 and 4
    
    # Instrument layers
    layers = {
        "steel_drum": create_melody_line(momentum_data, scale="major_pentatonic"),
        "marimba": create_harmony_pad(tempo, key="C"),
        "bass": create_walking_bass(tempo, feel="reggae"),
        "shaker": create_percussion_layer(rhythm_pattern),
        "vibes": create_sparkle_layer(momentum_data)  # Follows volatility
    }
    
    # Caribbean-specific modulations
    for i, band in enumerate(momentum_data):
        if band["score"] > 0.5:  # Positive momentum
            layers["steel_drum"][i] += add_tropical_flourish()
        if band["label"] == "negative":  # Price spikes
            layers["vibes"][i] += add_concern_dissonance()
    
    return layers
```

---

## 📊 **Frontend Integration (Lovable.dev)**

### **Theme Catalog Structure**
```json
// theme_catalog_travel.json
{
  "vertical": "travel",
  "themes": {
    "flights_from_nyc": {
      "title": "Flights from NYC",
      "description": "Where New Yorkers want to fly",
      "sub_themes": {
        "budget_carriers": {
          "title": "Budget Carriers",
          "description": "Spirit, Frontier, JetBlue deals",
          "sound_pack": "8-Bit",
          "color": "#FFD700",
          "icon": "✈️"
        },
        "legacy_airlines": {
          "title": "Legacy Airlines", 
          "description": "Delta, American, United premium",
          "sound_pack": "Arena Rock",
          "color": "#1E40AF",
          "icon": "🛫"
        },
        "red_eye_deals": {
          "title": "Red-Eye Deals",
          "description": "Late night cross-country",
          "sound_pack": "Synthwave", 
          "color": "#8B5CF6",
          "icon": "🌙"
        },
        "caribbean_kokomo": {
          "title": "Caribbean Kokomo",
          "description": "Island paradise from NYC",
          "sound_pack": "Tropical Pop",
          "color": "#10B981",
          "icon": "🏝️"
        }
      }
    }
  }
}
```

### **Enhanced Audio Controls (Kokomo Integration)**
```typescript
// Lovable frontend integration
interface KokomoThemeProps {
  destination: string;
  searchVolume: number;
  momentumData: MomentumBand[];
  soundPack: "Tropical Pop";
}

const KokomoPlayer: React.FC<KokomoThemeProps> = ({ 
  destination, 
  searchVolume, 
  momentumData, 
  soundPack 
}) => {
  const { playTrack, enableEarcons } = useEarcons();
  
  const handlePlayKokomo = () => {
    // Enable Caribbean-specific earcons
    enableEarcons({
      "volatility_spike": "crystal.ping",
      "destination_reveal": "steel_drum_roll",
      "price_drop": "wind_chime_down"
    });
    
    // Play with tropical pop sound pack
    playTrack({
      momentumData,
      soundPack: "Tropical Pop",
      tempo: 104,
      instruments: ["marimba", "steel_drum", "vibes"],
      theme: "caribbean_kokomo"
    });
  };
  
  return (
    <div className="kokomo-player bg-gradient-to-br from-cyan-400 to-green-400">
      <div className="flex items-center gap-4">
        <div className="text-2xl">🏝️</div>
        <div>
          <h3 className="font-semibold">NYC → {destination}</h3>
          <p className="text-sm opacity-75">{searchVolume.toLocaleString()} monthly searches</p>
        </div>
        <button 
          onClick={handlePlayKokomo}
          className="ml-auto bg-white/20 hover:bg-white/30 px-4 py-2 rounded-lg"
        >
          Play Kokomo Mix
        </button>
      </div>
    </div>
  );
};
```

---

## 🚀 **Deployment & Operations**

### **Environment Configuration**
```bash
# creds.env.txt (enhanced)
# OpenAI API for pipeline
OPENAI_API_KEY=sk-proj-...

# Supabase Storage 
SUPABASE_URL=https://bulcmonhcvqljorhiqgk.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...

# Storage buckets
STORAGE_BUCKET=serpradio-artifacts
PUBLIC_STORAGE_BUCKET=serpradio-public

# Multi-theme pipeline settings
DEFAULT_VERTICAL=travel
DEFAULT_THEME=flights_from_nyc
ENABLED_SUB_THEMES=budget_carriers,legacy_airlines,red_eye_deals,caribbean_kokomo

# Audio generation
RENDER_MP3=1
DEFAULT_TEMPO=120
TROPICAL_TEMPO=104  # Kokomo-specific

# Admin & scheduling
ADMIN_SECRET=sr_admin_2025_secure_secret
PIPELINE_SCHEDULE=0 8 * * *  # Daily 8AM UTC
```

### **Automated Pipeline Scheduling**
```yaml
# .github/workflows/daily-pipeline.yml
name: Daily SERP Radio Pipeline
on:
  schedule:
    - cron: '0 8 * * *'  # 8AM UTC daily
  workflow_dispatch:

jobs:
  generate-audio:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run multi-theme pipeline
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_ANON_KEY: ${{ secrets.SUPABASE_ANON_KEY }}
        run: |
          python -m src.pipeline.run_pipeline \
            --vertical travel \
            --theme flights_from_nyc \
            --sub-themes budget_carriers legacy_airlines red_eye_deals caribbean_kokomo \
            --tracks-per-theme 6 \
            --limit 24
      
      - name: Notify completion
        run: echo "🎵 Daily SERP Radio pipeline completed!"
```

---

## 📈 **Scaling Roadmap**

### **Phase 1: Enhanced NYC + Caribbean (Current)**
- ✅ Multi-theme architecture
- ✅ Budget/Legacy/Red-eye themes
- ✅ Caribbean Kokomo integration
- ✅ Tropical Pop sound pack
- ✅ Theme-aware earcons

### **Phase 2: Additional Verticals (Next Month)**
```
finance/
├── wall_street_march/
│   ├── tech_stocks/          # FAANG movements
│   ├── crypto_pulse/         # Bitcoin, ETH volatility
│   └── fed_watch/            # Interest rate impacts
└── nyc_real_estate/
    ├── manhattan_luxury/     # High-end market
    ├── brooklyn_emerging/    # Gentrification trends
    └── rental_pulse/         # Monthly rent changes

ecommerce/
├── deal_drums/
│   ├── amazon_prime/        # Prime Day, lightning deals
│   ├── retail_wars/         # Target vs Walmart pricing
│   └── brand_battles/       # Nike vs Adidas, etc.
└── holiday_shopping/
    ├── black_friday/        # Seasonal price drops
    ├── cyber_monday/        # Online deal frenzy
    └── post_holiday/        # Clearance events
```

### **Phase 3: Advanced Features (Future)**
- **Personalized Themes**: User preference-based generation
- **Real-time Triggers**: Market event-driven pipeline runs
- **Cross-Vertical Insights**: "Flights get cheaper when stocks drop"
- **Geographic Expansion**: "Flights from LA", "Flights from Chicago"
- **Advanced Earcons**: Location-specific sound signatures

---

## 🔧 **Technical Specifications**

### **Performance Targets**
- **Generation Speed**: 24 tracks in <5 minutes
- **Audio Quality**: 44.1kHz/16-bit MP3, professional mastering
- **Storage Efficiency**: <10MB per track, optimized compression
- **API Response**: <500ms for catalog queries
- **Uptime**: 99.9% availability for pipeline endpoints

### **Monitoring & Observability**
```python
# Enhanced logging for multi-theme pipeline
logger.info({
    "event": "pipeline_start",
    "vertical": vertical,
    "theme": theme,
    "sub_themes": sub_themes,
    "tracks_requested": limit,
    "estimated_duration": estimated_time
})

logger.info({
    "event": "theme_processed", 
    "sub_theme": sub_theme,
    "tracks_generated": len(plans),
    "avg_novelty_score": avg_novelty,
    "sound_pack_distribution": sound_pack_counts
})

logger.info({
    "event": "pipeline_complete",
    "total_tracks": len(entries),
    "duration_seconds": elapsed_time,
    "catalog_published": catalog_url,
    "storage_used_mb": storage_mb
})
```

---

This comprehensive architecture supports infinite scaling across verticals while maintaining the core NYC focus and emotional/nostalgic sound mapping that makes SERP Radio unique. The Caribbean Kokomo theme adds tropical flavor while the technical foundation supports rapid expansion to finance, e-commerce, and beyond! 🎵🏝️🏙️