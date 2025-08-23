import os, requests
from typing import Iterable
from .normalize import normalize_offer

TEQUILA_API_KEY = os.environ.get("TEQUILA_API_KEY","")
TEQUILA_ENDPOINT = "https://tequila-api.kiwi.com/v2/search"

def search_one_day(origin_airport: str, dest_airport: str, date_iso: str, nonstop_only: bool=True) -> Iterable[dict]:
    if not TEQUILA_API_KEY:
        raise RuntimeError("TEQUILA_API_KEY missing")
    headers = {"apikey": TEQUILA_API_KEY}
    params = {
        "fly_from": origin_airport,
        "fly_to": dest_airport,
        "date_from": date_iso,
        "date_to": date_iso,
        "curr": "USD",
        "limit": 50,
        "max_stopovers": 0 if nonstop_only else 2,
        "sort": "price"
    }
    r = requests.get(TEQUILA_ENDPOINT, headers=headers, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    for it in data.get("data", []):
        yield normalize_offer("kiwi", it)
