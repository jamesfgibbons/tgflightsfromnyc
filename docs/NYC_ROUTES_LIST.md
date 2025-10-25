# 🛫 NYC Flight Routes - Complete List

## Overview

**NYC Airports (Origins): 3**
- JFK - John F. Kennedy International Airport
- EWR - Newark Liberty International Airport
- LGA - LaGuardia Airport

**Destinations: 20** (Top US routes from NYC)

**Total Routes: 60** (3 origins × 20 destinations)

---

## 📍 All 60 Routes

### From JFK (20 routes)

| Route | Destination | City | Price Range |
|-------|-------------|------|-------------|
| JFK→MIA | Miami International | Miami, FL | $180-$350 |
| JFK→LAX | Los Angeles International | Los Angeles, CA | $250-$500 |
| JFK→SFO | San Francisco International | San Francisco, CA | $280-$550 |
| JFK→ORD | O'Hare International | Chicago, IL | $150-$300 |
| JFK→ATL | Hartsfield-Jackson | Atlanta, GA | $140-$280 |
| JFK→DEN | Denver International | Denver, CO | $200-$400 |
| JFK→LAS | Harry Reid International | Las Vegas, NV | $180-$380 |
| JFK→SEA | Seattle-Tacoma International | Seattle, WA | $300-$600 |
| JFK→PHX | Phoenix Sky Harbor | Phoenix, AZ | $220-$440 |
| JFK→MCO | Orlando International | Orlando, FL | $160-$320 |
| JFK→FLL | Fort Lauderdale-Hollywood | Fort Lauderdale, FL | $170-$340 |
| JFK→SAN | San Diego International | San Diego, CA | $260-$520 |
| JFK→DCA | Ronald Reagan Washington | Washington, DC | $120-$250 |
| JFK→DFW | Dallas/Fort Worth | Dallas, TX | $200-$400 |
| JFK→IAH | George Bush Houston | Houston, TX | $200-$400 |
| JFK→BOS | Boston Logan | Boston, MA | $80-$180 |
| JFK→CLT | Charlotte Douglas | Charlotte, NC | $130-$260 |
| JFK→DTW | Detroit Metro Wayne | Detroit, MI | $150-$300 |
| JFK→MSP | Minneapolis-St. Paul | Minneapolis, MN | $180-$360 |
| JFK→PHL | Philadelphia International | Philadelphia, PA | $100-$200 |

### From EWR (20 routes)

| Route | Destination | City | Price Range |
|-------|-------------|------|-------------|
| EWR→MIA | Miami International | Miami, FL | $180-$350 |
| EWR→LAX | Los Angeles International | Los Angeles, CA | $250-$500 |
| EWR→SFO | San Francisco International | San Francisco, CA | $280-$550 |
| EWR→ORD | O'Hare International | Chicago, IL | $150-$300 |
| EWR→ATL | Hartsfield-Jackson | Atlanta, GA | $140-$280 |
| EWR→DEN | Denver International | Denver, CO | $200-$400 |
| EWR→LAS | Harry Reid International | Las Vegas, NV | $180-$380 |
| EWR→SEA | Seattle-Tacoma International | Seattle, WA | $300-$600 |
| EWR→PHX | Phoenix Sky Harbor | Phoenix, AZ | $220-$440 |
| EWR→MCO | Orlando International | Orlando, FL | $160-$320 |
| EWR→FLL | Fort Lauderdale-Hollywood | Fort Lauderdale, FL | $170-$340 |
| EWR→SAN | San Diego International | San Diego, CA | $260-$520 |
| EWR→DCA | Ronald Reagan Washington | Washington, DC | $120-$250 |
| EWR→DFW | Dallas/Fort Worth | Dallas, TX | $200-$400 |
| EWR→IAH | George Bush Houston | Houston, TX | $200-$400 |
| EWR→BOS | Boston Logan | Boston, MA | $80-$180 |
| EWR→CLT | Charlotte Douglas | Charlotte, NC | $130-$260 |
| EWR→DTW | Detroit Metro Wayne | Detroit, MI | $150-$300 |
| EWR→MSP | Minneapolis-St. Paul | Minneapolis, MN | $180-$360 |
| EWR→PHL | Philadelphia International | Philadelphia, PA | $100-$200 |

### From LGA (20 routes)

| Route | Destination | City | Price Range |
|-------|-------------|------|-------------|
| LGA→MIA | Miami International | Miami, FL | $180-$350 |
| LGA→LAX | Los Angeles International | Los Angeles, CA | $250-$500 |
| LGA→SFO | San Francisco International | San Francisco, CA | $280-$550 |
| LGA→ORD | O'Hare International | Chicago, IL | $150-$300 |
| LGA→ATL | Hartsfield-Jackson | Atlanta, GA | $140-$280 |
| LGA→DEN | Denver International | Denver, CO | $200-$400 |
| LGA→LAS | Harry Reid International | Las Vegas, NV | $180-$380 |
| LGA→SEA | Seattle-Tacoma International | Seattle, WA | $300-$600 |
| LGA→PHX | Phoenix Sky Harbor | Phoenix, AZ | $220-$440 |
| LGA→MCO | Orlando International | Orlando, FL | $160-$320 |
| LGA→FLL | Fort Lauderdale-Hollywood | Fort Lauderdale, FL | $170-$340 |
| LGA→SAN | San Diego International | San Diego, CA | $260-$520 |
| LGA→DCA | Ronald Reagan Washington | Washington, DC | $120-$250 |
| LGA→DFW | Dallas/Fort Worth | Dallas, TX | $200-$400 |
| LGA→IAH | George Bush Houston | Houston, TX | $200-$400 |
| LGA→BOS | Boston Logan | Boston, MA | $80-$180 |
| LGA→CLT | Charlotte Douglas | Charlotte, NC | $130-$260 |
| LGA→DTW | Detroit Metro Wayne | Detroit, MI | $150-$300 |
| LGA→MSP | Minneapolis-St. Paul | Minneapolis, MN | $180-$360 |
| LGA→PHL | Philadelphia International | Philadelphia, PA | $100-$200 |

---

## 🌍 Destinations by Region

### Florida (4 destinations)
- MIA - Miami
- MCO - Orlando
- FLL - Fort Lauderdale
- (Total: 12 routes = 3 origins × 4 destinations)

### California (3 destinations)
- LAX - Los Angeles
- SFO - San Francisco
- SAN - San Diego
- (Total: 9 routes = 3 origins × 3 destinations)

### Texas (2 destinations)
- DFW - Dallas/Fort Worth
- IAH - Houston
- (Total: 6 routes = 3 origins × 2 destinations)

### East Coast (5 destinations)
- DCA - Washington DC
- BOS - Boston
- PHL - Philadelphia
- CLT - Charlotte
- ATL - Atlanta
- (Total: 15 routes = 3 origins × 5 destinations)

### Midwest (3 destinations)
- ORD - Chicago
- DTW - Detroit
- MSP - Minneapolis
- (Total: 9 routes = 3 origins × 3 destinations)

### Mountain/West (3 destinations)
- DEN - Denver
- LAS - Las Vegas
- PHX - Phoenix
- SEA - Seattle
- (Total: 9 routes = 3 origins × 3 destinations)

---

## 📊 Route Configuration

### In Code (src/worker_refresh.py)

```python
# NYC Origins (3 airports)
NYC_ORIGINS = os.getenv("NYC_ORIGINS", "JFK,EWR,LGA").split(",")

# Top 20 Destinations
DEFAULT_DESTINATIONS = "MIA,LAX,SFO,ORD,ATL,DEN,LAS,SEA,PHX,MCO,FLL,SAN,DCA,DFW,IAH,BOS,CLT,DTW,MSP,PHL"
TOP_DESTINATIONS = os.getenv("TOP_DESTINATIONS", DEFAULT_DESTINATIONS).split(",")

# Result: 3 × 20 = 60 routes
```

### Customizable via Environment Variables

**Add more origins:**
```bash
export NYC_ORIGINS=JFK,EWR,LGA,HPN
# Adds White Plains (4 origins × 20 dests = 80 routes)
```

**Add more destinations:**
```bash
export TOP_DESTINATIONS=MIA,LAX,SFO,ORD,ATL,DEN,LAS,SEA,PHX,MCO,FLL,SAN,DCA,DFW,IAH,BOS,CLT,DTW,MSP,PHL,TPA,JAX,RDU,BWI,MDW
# 25 destinations × 3 origins = 75 routes
```

---

## 🎯 Coverage Analysis

### Current Coverage: Good ✅

**Top 20 US Destinations from NYC:**
1. ✅ Florida markets (MIA, MCO, FLL) - High frequency leisure
2. ✅ California (LAX, SFO, SAN) - Major west coast hubs
3. ✅ Business hubs (ORD, ATL, DFW, IAH) - High frequency business
4. ✅ East coast (BOS, DCA, PHL, CLT) - Shuttle routes
5. ✅ Leisure (LAS, PHX, DEN, SEA) - Popular vacation destinations

### Potential Additions

**If you want more coverage, consider adding:**

**Florida:**
- TPA - Tampa
- JAX - Jacksonville
- RSW - Fort Myers
- PBI - West Palm Beach

**East Coast:**
- BWI - Baltimore
- RDU - Raleigh-Durham
- RIC - Richmond
- PVD - Providence

**Midwest:**
- MDW - Chicago Midway (alternative to ORD)
- STL - St. Louis
- CLE - Cleveland
- MKE - Milwaukee

**West Coast:**
- PDX - Portland
- SLC - Salt Lake City
- SMF - Sacramento
- SJC - San Jose

**International (if API supports):**
- YYZ - Toronto
- YUL - Montreal
- CUN - Cancun
- SJU - San Juan

---

## 🚀 How Routes Are Used

### Price Worker (every 6 hours)
```python
# Generates all route combinations
routes = []
for origin in ["JFK", "EWR", "LGA"]:
    for dest in [20 destinations]:
        routes.append((origin, dest))

# Result: 60 routes
# Batches: 1 batch (under 100 route limit)
# Windows: 6 months (monthly windows)
# Total queries: 60 routes × 6 windows = 360 API calls
# Expected results: ~5,000-10,000 price observations
```

### Deal Awareness API
```bash
# Users can query any route:
GET /api/deals/evaluate?origin=JFK&dest=MIA&month=3
GET /api/deals/evaluate?origin=EWR&dest=LAX&month=6
GET /api/deals/evaluate?origin=LGA&dest=BOS&month=1
```

### Board Feed
```bash
# Shows all routes with recent activity:
GET /api/board/feed?origins=JFK,EWR,LGA&limit=20
# Returns split-flap display data for all 60 routes
```

---

## ✅ Summary

**Current Configuration:**
- ✅ 3 NYC airports (JFK, EWR, LGA)
- ✅ 20 top US destinations
- ✅ 60 total routes
- ✅ Comprehensive coverage of major markets
- ✅ Easily expandable via environment variables

**Coverage Quality:**
- ✅ Business travel: Excellent (ORD, ATL, DFW, IAH, etc.)
- ✅ Leisure travel: Excellent (MIA, MCO, LAS, etc.)
- ✅ East coast shuttles: Excellent (BOS, DCA, PHL)
- ✅ West coast: Good (LAX, SFO, SAN, SEA)
- ✅ Price diversity: $80-$600 range

**Recommendation:**
The current 60 routes provide excellent coverage of NYC flight patterns. This is a solid foundation - you can always expand later by updating the environment variables.

---

**Want to add more routes?** Just update the environment variable:

```bash
# Railway/GitHub Actions environment:
TOP_DESTINATIONS=MIA,LAX,SFO,ORD,ATL,DEN,LAS,SEA,PHX,MCO,FLL,SAN,DCA,DFW,IAH,BOS,CLT,DTW,MSP,PHL,TPA,JAX
# Now: 3 origins × 22 destinations = 66 routes
```
