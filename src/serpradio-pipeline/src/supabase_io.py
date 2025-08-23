import os
import hashlib
from supabase import create_client, Client

def _client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ.get("SUPABASE_SERVICE_ROLE") or os.environ["SUPABASE_ANON_KEY"]
    return create_client(url, key)

def upsert_offers(rows, source: str):
    """Upsert flight offers to flight_price_data table using the simplified schema"""
    if not rows: 
        print("ℹ️ No offers to upsert")
        return
    
    sb = _client()
    payload = []
    
    for r in rows:
        # Generate deterministic id from key fields
        key_str = f"{r['origin']}-{r['destination']}-{r['departure_date']}-{r['brand']}-{r['price_cents']}"
        offer_id = hashlib.sha256(key_str.encode()).hexdigest()[:16]
        
        payload.append({
            "id": offer_id,
            "origin": r["origin"],
            "destination": r["destination"],
            "departure_date": r["departure_date"],
            "airline": r["brand"],  # canonical brand name
            "price": r["price_cents"] / 100.0,  # Convert cents to dollars
            "currency": r["currency"],
            "direct_flight": r.get("nonstop", True),
            "data_source": source  # 'openai' or 'openai_generated'
        })
    
    # Upsert to flight_price_data table
    try:
        result = sb.table("flight_price_data").upsert(
            payload, 
            on_conflict="id"
        ).execute()
        print(f"✅ Upserted {len(payload)} offers to flight_price_data from {source}")
        return result
    except Exception as e:
        print(f"❌ Upsert failed: {e}")
        raise