#!/usr/bin/env python3
"""
CLI entry to run the Webz.io consumer loop.

Usage:
  WEBZIO_API_TOKEN=... python scripts/run_webzio_consumer.py

Optional env:
  WEBZIO_FIREHOSE_URL, WEBZIO_FILTER, WEBZIO_OUTPUT_DATASET_PATH,
  WEBZIO_TIMEOUT, WEBZIO_RETRIES, WEBZIO_BACKOFF_SEC
"""
from __future__ import annotations
from src.webzio_integration import load_config_from_env, run_consumer_loop


def main():
    cfg = load_config_from_env()
    run_consumer_loop(cfg)


if __name__ == "__main__":
    main()

