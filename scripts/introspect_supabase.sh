#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${SUPABASE_DB_URL:-}" ]]; then
  echo "SUPABASE_DB_URL not set. Example: postgresql://postgres:[PASS]@db.<ref>.supabase.co:5432/postgres" >&2
  exit 1
fi

psql "$SUPABASE_DB_URL" -f tools/introspect_schema.sql | tee supabase_schema_dump.txt
echo "\nWrote supabase_schema_dump.txt"

