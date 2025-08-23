#!/usr/bin/env bash
set -euo pipefail
export $(cat creds.env.txt | grep -v '^#' | xargs)
python -m src.pipeline.build_momentum --days ${DAYS:-7}
