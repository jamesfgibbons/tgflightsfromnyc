#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "🧠 SERP Radio — OpenAI Cache Builder"
export $(grep -v '^#' creds.env.txt | xargs)

# Example: build JSON-only "visibility insight" cache for the last N days
python - <<'PY'
import os, json, time, datetime as dt
from supabase import create_client
from openai import OpenAI

N_DAYS = int(os.getenv("CACHE_WINDOW_DAYS","7"))
MODEL = os.getenv("CACHE_MODEL","gpt-4o-mini")

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE"])
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

# Pull recent top Caribbean rows from your ETL outputs or views (adjust table if needed)
# Here we assume visibility is materialized in a table named flight_visibility (Caribbean only).
r = sb.table("flight_visibility").select("*").eq("region","caribbean").gte("date_bucket", str(dt.date.today()-dt.timedelta(days=N_DAYS))).limit(600).execute()

msgs=[{"role":"system","content":"Return STRICT JSON with keys: price_range, brand_leaders, volatility_note, novelty, kokomo_hint"}]
for row in r.data:
    msgs.append({"role":"user","content":json.dumps({
        "origin":row.get("origin","NYC"),
        "destination":row.get("destination","SJU"),
        "price_median":row.get("price_median"),
        "price_p25":row.get("price_p25"),
        "price_p75":row.get("price_p75"),
        "volatility":row.get("volatility"),
        "sov_brand":row.get("sov_brand",{})
    })})

resp = client.chat.completions.create(
    model=MODEL,
    temperature=0.2,
    response_format={"type":"json_object"},
    messages=msgs
)

# Store a single consolidated cache blob (or split per-row as you prefer)
payload = {"model": MODEL, "generated_at": dt.datetime.utcnow().isoformat(), "data": json.loads(resp.choices[0].message.content)}
sb.table("cache_jobs").insert({
    "prompt_key":"caribbean_daily_cache",
    "prompt_hash":"caribbean_daily_cache_v1",
    "model":MODEL,
    "status":"succeeded",
    "payload":payload
}).execute()
print("✅ Cache built")
PY