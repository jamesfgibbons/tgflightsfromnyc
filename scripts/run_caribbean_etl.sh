#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "🏝️ SERP Radio — Caribbean ETL"
export $(grep -v '^#' creds.env.txt | xargs)

# Optional: pass a CSV path; otherwise ETL will generate realistic sample data
# Example CSV (GSC export) path: data/google_us_caribbean_keywords.csv
CSV_PATH="${1:-}"

# Python entry (uses UnifiedStorage + writes latest_summary.json)
python - <<'PY'
import asyncio, os, sys
from dotenv import load_dotenv
load_dotenv("creds.env.txt")
# Uses your Caribbean ETL which loads CSV or samples and writes catalog + summary
from src.pipeline.caribbean_etl import CaribbeanETL  # module path aligned with your repo layout
async def main():
    etl = CaribbeanETL(storage_bucket=os.getenv("STORAGE_BUCKET","serpradio-artifacts"))
    res = await etl.run_caribbean_etl(csv_path=os.environ.get("CSV_PATH",""), output_prefix="caribbean_kokomo")
    print(res)
os.environ["CSV_PATH"] = sys.argv[1] if len(sys.argv)>1 else ""
asyncio.run(main())
PY