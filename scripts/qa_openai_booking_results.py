#!/usr/bin/env python3
"""
QA analyzer for OpenAI 'best time to book' results (cached files and/or Supabase).

Validates that responses are strict JSON with required fields and sane values.
Outputs a summary report and writes failure details to CSV/JSON.

Default mode: scan cache dir (LLM_CACHE_DIR or serpradio_convo_cache) for
OpenAI records (openai_*.json) and validate each record.

Optional: --from-supabase to fetch recent rows where metadata.kind='best_time_to_book'.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
import csv
from pathlib import Path
from typing import Any, Dict, List, Tuple


def cache_dir() -> Path:
    return Path(os.getenv("LLM_CACHE_DIR", "serpradio_convo_cache"))


def iter_cache_records(limit: int | None = None):
    d = cache_dir()
    if not d.exists():
        return
    count = 0
    for p in d.glob("openai_*.json"):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
            rec["__file"] = str(p)
            yield rec
            count += 1
            if limit and count >= limit:
                break
        except Exception:
            yield {"__file": str(p), "__error": "invalid_json_file"}


def get_prompt_route(prompt: str) -> Tuple[str | None, str | None]:
    # Extract origin/destination from embedded JSON fields in the prompt line
    mo = re.search(r'"origin":\s*"(JFK|LGA|EWR)"', prompt)
    md = re.search(r'"destination":\s*"([A-Z]{3})"', prompt)
    return (mo.group(1) if mo else None, md.group(1) if md else None)


def parse_openai_content(resp: Dict[str, Any]) -> Tuple[Dict[str, Any] | None, str | None]:
    try:
        choices = resp.get("response_raw", {}).get("choices") or []
        if not choices:
            return None, "no_choices"
        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str):
            return None, "content_not_string"
        data = json.loads(content)
        if not isinstance(data, dict):
            return None, "content_not_object"
        return data, None
    except Exception as e:
        return None, f"parse_error:{e}"


def validate_schema(data: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    def req_str(k):
        v = data.get(k)
        if not isinstance(v, str) or not v.strip():
            errs.append(f"{k}:missing_or_not_string")
        return v
    def req_num(k):
        v = data.get(k)
        if not isinstance(v, (int, float)):
            errs.append(f"{k}:missing_or_not_number")
        return v
    origin = req_str("origin")
    dest = req_str("destination")
    window = req_num("window_days")
    bl = data.get("best_window_days")
    if not (isinstance(bl, list) and len(bl) == 2 and all(isinstance(x, (int, float)) for x in bl)):
        errs.append("best_window_days:invalid")
    else:
        lo, hi = bl
        if lo < 0 or hi < 0 or hi < lo or hi > 365:
            errs.append("best_window_days:unreasonable")
    low = req_num("fare_low_usd")
    high = req_num("fare_high_usd")
    if isinstance(low, (int, float)) and isinstance(high, (int, float)):
        if low < 0 or high < 0 or high < low:
            errs.append("fare_range:unreasonable")
    notes = data.get("notes")
    if not isinstance(notes, str) or not notes.strip():
        errs.append("notes:missing")
    # optional: origin/destination format
    if isinstance(origin, str) and origin not in {"JFK","LGA","EWR"}:
        errs.append("origin:not_nyc")
    if isinstance(dest, str) and not re.fullmatch(r"[A-Z]{3}", dest):
        errs.append("destination:bad_iata")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--from-supabase", action="store_true")
    ap.add_argument("--out-json", default="data/qa_booking_report.json")
    ap.add_argument("--out-csv", default="data/qa_booking_failures.csv")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out_json) or ".", exist_ok=True)

    total = 0
    ok = 0
    parse_err = 0
    schema_err = 0
    mismatches = 0
    failures: List[Dict[str, Any]] = []

    # Iterate cache by default
    for rec in iter_cache_records(limit=args.limit):
        total += 1
        fpath = rec.get("__file")
        if rec.get("__error"):
            parse_err += 1
            failures.append({"file": fpath, "error": rec["__error"], "prompt": None})
            continue
        prompt: str = rec.get("prompt", "")
        data, perr = parse_openai_content(rec)
        if perr:
            parse_err += 1
            failures.append({"file": fpath, "error": perr, "prompt": prompt[:200]})
            continue
        errs = validate_schema(data)
        porig, pdest = get_prompt_route(prompt)
        if porig and pdest:
            if (data.get("origin") != porig) or (data.get("destination") != pdest):
                errs.append("route_mismatch")
                mismatches += 1
        if errs:
            schema_err += 1
            failures.append({
                "file": fpath,
                "error": ",".join(errs),
                "prompt": prompt[:200],
                "data": data
            })
        else:
            ok += 1

    report = {
        "total": total,
        "ok": ok,
        "parse_errors": parse_err,
        "schema_errors": schema_err,
        "route_mismatches": mismatches,
        "cache_dir": str(cache_dir()),
    }
    print(json.dumps(report, indent=2))
    with open(args.out_json, "w", encoding="utf-8") as f:
        json.dump({"report": report, "failures": failures}, f, ensure_ascii=False, indent=2)
    if failures:
        with open(args.out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["file","error","prompt","data"])
            w.writeheader()
            for row in failures:
                w.writerow({k: (json.dumps(row[k]) if isinstance(row.get(k), (dict, list)) else row.get(k)) for k in ["file","error","prompt","data"]})


if __name__ == "__main__":
    main()

