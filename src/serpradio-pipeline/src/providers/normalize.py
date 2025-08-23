# Normalization helper to map provider JSON into a single Offer schema.
import hashlib
from src.geo_registry import ORIGIN_METRO, DEST_REGION, DEST_COUNTRY

def normalize_offer(source: str, it: dict) -> dict:
    # Expect Kiwi/Tequila-like shape; adjust as needed.
    route = it.get("route", [])
    first = route[0] if route else {}
    departure = first.get("local_departure","0000-00-00T00:00:00")  # ISO string
    dep_iso = departure[:10]
    dep_hour = int(departure[11:13]) if "T" in departure else 0
    time_window = "red_eye" if dep_hour < 6 else ("am" if dep_hour < 12 else "pm")

    origin = it.get("flyFrom")
    dest = it.get("flyTo")
    price = float(it.get("price", 0))
    carrier = first.get("airline","XX")
    carrier_name = (it.get("airlines_names") or [carrier])[0]
    seller_name = it.get("deep_link_domain") or it.get("booking_provider") or "Unknown"

    stops = max(0, len(route) - 1)

    oid = f"{origin}|{dest}|{dep_iso}|{carrier}|{seller_name}|{price}"
    offer_id = hashlib.sha256(oid.encode()).hexdigest()

    return {
      "offer_id": offer_id,
      "origin_airport": origin,
      "origin_metro": ORIGIN_METRO.get(origin, origin),
      "dest_airport": dest,
      "dest_region": DEST_REGION.get(dest, "other"),
      "dest_country": DEST_COUNTRY.get(dest, "XX"),
      "date_depart": dep_iso,
      "time_window": time_window,
      "nonstop": stops == 0,
      "stops": stops,
      "carrier": carrier,
      "carrier_name": carrier_name,
      "fare_brand": it.get("fare_category") or "Unknown",
      "baggage_included": 1 if it.get("bags_price",{}).get("1","0") == "0" else 0,
      "seller_type": "airline" if seller_name.endswith(".com") and carrier.lower() in seller_name.lower() else "OTA",
      "seller_name": seller_name,
      "price_usd": price,
      "currency": "USD",
      "source": source,
      "raw": {"id": it.get("id","")}
    }
