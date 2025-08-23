#!/usr/bin/env bash
set -euo pipefail

# Load environment (creds.env.txt should define OPENAI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE, optional TAVILY_API_KEY)
if [ -f "./creds.env.txt" ]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' ./creds.env.txt | xargs)
fi

# Defaults for testing
export OPENAI_MODEL=${OPENAI_MODEL:-gpt-4o-mini}
export OPENAI_TEMP=${OPENAI_TEMP:-0.2}
export OPENAI_MAX_TOKENS=${OPENAI_MAX_TOKENS:-700}
export REGION=${REGION:-caribbean}
export RUN_ID=${RUN_ID:-$(date -u +"%Y%m%dT%H%M%SZ")}

echo "🟢 Conversational cache run: REGION=$REGION RUN_ID=$RUN_ID MODEL=$OPENAI_MODEL"
python3 -m src.pipeline.convo_cache --day "${DAY_PHRASE:-tomorrow}" --max-dests "${MAX_DESTS:-8}" --max-results "${MAX_RESULTS:-5}"
echo "✅ Done."
