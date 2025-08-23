# 🏗️ SERP Radio - Scalable Multi-Vertical Architecture

## 🎯 **Core Design Principles**

### **1. Vertical-First Architecture**
```
verticals/
├── travel/           # Current focus: Flights from NYC
├── finance/          # Future: Stock prices, crypto, forex
├── ecommerce/        # Future: Product prices, deals, reviews
├── real_estate/      # Future: Housing prices, rent trends
└── shared/           # Common utilities and base classes
```

### **2. Theme-Based Granularity**
Each vertical can have multiple themes with increasing specificity:

```
travel/
├── flights_from_nyc/     # ⭐ CURRENT FOCUS
│   ├── budget_carriers/  # Spirit, Frontier, JetBlue
│   ├── legacy_airlines/  # Delta, American, United
│   ├── international/    # NYC to Europe, Asia
│   └── seasonal/         # Holiday routes, summer destinations
├── hotels/               # Future expansion
├── car_rentals/         # Future expansion
└── cruises/             # Future expansion
```

### **3. Sound Pack Emotional Mapping**
```
travel/flights_from_nyc/
├── budget_carriers/ → 8-Bit (playful, frugal, nostalgic)
├── legacy_airlines/ → Arena Rock (confident, established)
├── international/   → Synthwave (exotic, dreamy)
└── red_eye_deals/   → Ambient (late night, mysterious)
```

---

## 🎵 **Enhanced "Flights from NYC" Theme**

### **Current Focus: Maximum Granularity**

#### **Geographic Precision**
- **Origins**: JFK, LGA, EWR, HPN (White Plains), ISP (Long Island), SWF (Stewart)
- **Destination Tiers**:
  - **Tier 1**: LAS, MIA, LAX, MCO (high volume routes)
  - **Tier 2**: BOS, ATL, DFW, ORD (business routes) 
  - **Tier 3**: International hubs (LHR, CDG, NRT)

#### **Carrier Personality Mapping**
- **Budget Carriers**: 
  - Spirit → 8-Bit (ultra-budget, no-frills)
  - Frontier → 8-Bit (animal tails, playful)
  - JetBlue → Synthwave (trendy, mint green)
- **Legacy Carriers**:
  - Delta → Arena Rock (premium, confident)
  - American → Arena Rock (traditional, powerful)
  - United → Arena Rock (global reach)
- **International**:
  - Virgin Atlantic → Synthwave (cool, modern)
  - British Airways → Arena Rock (classic, refined)

#### **Time-Based Themes**
- **Red-eye flights** (11PM-6AM) → Ambient/Synthwave (mysterious, nocturnal)
- **Business hours** (6AM-6PM) → Arena Rock (professional, urgent)
- **Weekend leisure** → 8-Bit (fun, relaxed)

---

## 🔄 **Scalable Pipeline Architecture**

### **1. Vertical Manager**
```python
class VerticalManager:
    def __init__(self):
        self.verticals = {
            'travel': TravelVertical(),
            'finance': FinanceVertical(),    # Future
            'ecommerce': EcommerceVertical()  # Future
        }
    
    def get_active_themes(self, vertical: str) -> List[Theme]:
        return self.verticals[vertical].get_themes()
    
    def run_pipeline(self, vertical: str, theme: str = None):
        return self.verticals[vertical].run_pipeline(theme)
```

### **2. Theme Hierarchy**
```python
class Theme:
    def __init__(self, name: str, parent: str = None):
        self.name = name
        self.parent = parent
        self.sound_pack_mapping = {}
        self.prompt_library = {}
        self.nostalgia_factors = {}

class TravelVertical:
    def __init__(self):
        self.themes = {
            'flights_from_nyc': FlightsFromNYCTheme(),
            'hotels': HotelsTheme(),         # Future
            'car_rentals': CarRentalsTheme() # Future
        }
```

### **3. Enhanced Storage Structure**
```
Supabase Storage Layout:
serpradio-artifacts/
├── verticals/
│   ├── travel/
│   │   ├── flights_from_nyc/
│   │   │   ├── budget_carriers/
│   │   │   │   ├── midi/2025-08-16/
│   │   │   │   └── mp3/2025-08-16/
│   │   │   ├── legacy_airlines/
│   │   │   └── international/
│   │   └── hotels/              # Future
│   └── finance/                 # Future

serpradio-public/
├── catalog/
│   ├── travel/
│   │   ├── flights_from_nyc/
│   │   │   ├── latest.json
│   │   │   ├── budget_carriers.json
│   │   │   └── legacy_airlines.json
│   │   └── aggregate.json
│   └── finance/                 # Future
```

---

## 🎯 **Immediate Implementation: NYC Flights Focus**

### **Phase 1: Enhanced NYC Flight Granularity**

#### **1. Carrier-Specific Prompt Libraries**
```yaml
# src/pipeline/prompt_library/travel/flights_from_nyc/budget_carriers.yaml
channel: travel
theme: flights_from_nyc
sub_theme: budget_carriers
focus: "Ultra-budget NYC to vacation destinations"
carriers: [Spirit, Frontier, JetBlue]
sound_pack_default: "8-Bit"

origins: [JFK, LGA, EWR]
destinations:
  - code: LAS
    name: Las Vegas
    peak_season: "year-round"
  - code: MIA
    name: Miami  
    peak_season: "winter"
  - code: MCO
    name: Orlando
    peak_season: "summer"

templates:
  - "Find absolute rock-bottom Spirit flight {origin} to {dest} next 30 days"
  - "Frontier sales and mistake fares {origin} -> {dest} under $75"
  - "JetBlue Mint vs basic economy {origin} to {dest} price comparison"
  - "Hidden city routing through {dest} departing {origin} budget carriers only"

novelty_special:
  - "What's the most creative sub-$50 Spirit routing from any NYC airport to Vegas?"
  - "JetBlue flash sales NYC to Florida - when do they typically drop?"
```

#### **2. Time-Based Sub-Themes**
```yaml
# src/pipeline/prompt_library/travel/flights_from_nyc/red_eye_deals.yaml
channel: travel
theme: flights_from_nyc
sub_theme: red_eye_deals
focus: "Late night departures NYC to West Coast"
sound_pack_default: "Synthwave"
mood: "nocturnal, mysterious, deal-hunting"

time_windows:
  - departure: "11:00 PM - 2:00 AM"
    arrival: "2:00 AM - 6:00 AM"
    
destinations:
  - code: LAX
    name: Los Angeles
    red_eye_premium: "cross-country classic"
  - code: SFO
    name: San Francisco
    red_eye_premium: "tech commuter"
  - code: LAS
    name: Las Vegas
    red_eye_premium: "gambler special"

templates:
  - "Cheapest red-eye {origin} to {dest} departing after 11 PM"
  - "Late night mistake fares {origin} -> {dest} under $100"
  - "Red-eye vs early morning price difference {origin} to {dest}"
  - "JetRed-eye sleep-friendly routes {origin} to {dest} with lie-flat"
```

#### **3. Seasonal & Event-Driven Themes**
```yaml
# src/pipeline/prompt_library/travel/flights_from_nyc/seasonal_vegas.yaml
channel: travel
theme: flights_from_nyc
sub_theme: seasonal_vegas
focus: "NYC to Las Vegas seasonal pricing patterns"
sound_pack_default: "Synthwave"

seasonal_patterns:
  - season: "March Madness"
    dates: "March 15-31"
    price_multiplier: 2.5
  - season: "CES/NAB"
    dates: "January, April"
    price_multiplier: 3.0
  - season: "Summer Heat"
    dates: "June-August" 
    price_multiplier: 0.7

templates:
  - "NYC to Vegas during {season} - best deals avoiding peak {dates}"
  - "Price patterns {origin} to LAS during {season} vs normal weeks"
  - "Convention surge pricing {origin} -> LAS how to beat the crowds"
```

---

## 🚀 **Implementation Strategy**

### **Immediate (This Week)**
1. **Enhance current travel.yaml** with deeper NYC specificity
2. **Create carrier-specific sub-libraries** (budget vs legacy)
3. **Add time-based themes** (red-eye, business hours, weekend)
4. **Implement theme-aware catalog structure**

### **Short Term (Next 2 Weeks)** 
1. **Multi-theme pipeline support** - run multiple themes per batch
2. **Advanced nostalgia mapping** - time of day affects sound pack selection
3. **Seasonal awareness** - incorporate date-based pricing patterns
4. **Enhanced catalog structure** - theme-specific JSON files

### **Medium Term (Next Month)**
1. **Add second vertical** (finance: crypto/stocks from NYC perspective)
2. **Cross-theme insights** - "flights get cheaper when stocks go up"
3. **Dynamic theme scheduling** - different themes run on different days
4. **Advanced personalization** - user preference-based theme selection

---

## 💡 **NYC-Centric Expansion Ideas**

### **Travel Vertical Extensions**
- **NYC Hotel Deals** → Compare Manhattan vs Brooklyn vs Queens pricing
- **NYC Restaurant Reservations** → OpenTable availability sonification  
- **NYC Parking** → SpotHero, ParkWhiz dynamic pricing
- **NYC Transit** → MTA delay patterns, Uber surge pricing

### **Finance Vertical (NYC Focus)**
- **NYC Real Estate** → Manhattan apartment prices, Brooklyn trends
- **Local Stocks** → Companies headquartered in NYC (Goldman, JPM, etc.)
- **NYC Tax Impact** → How local tax changes affect pricing

### **Lifestyle Vertical (NYC Focus)**
- **Broadway Shows** → Ticket availability and pricing patterns
- **NYC Events** → Concert tickets, sporting events pricing
- **Weather Impact** → How weather affects flight delays, pricing

---

This architecture allows us to:
1. **Scale vertically** (new industries) and **horizontally** (themes within industries)
2. **Maintain the NYC focus** while expanding scope
3. **Preserve emotional/nostalgic mapping** across themes
4. **Support complex pipeline orchestration** for multiple themes
5. **Enable personalized theme selection** based on user preferences

Ready to implement the enhanced NYC flights theme? 🛫🎵