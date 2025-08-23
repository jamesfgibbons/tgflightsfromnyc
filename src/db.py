"""
Lightweight Supabase DB helpers using the existing storage client.
Falls back to no-ops when Supabase is not configured.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, Optional, List

from .storage import get_storage_backend, get_supabase_client, StorageError

logger = logging.getLogger(__name__)


def _client():
    if get_storage_backend() != "supabase":
        return None
    try:
        return get_supabase_client()
    except StorageError as e:
        logger.warning(f"Supabase unavailable: {e}")
        return None


def supabase_insert(table: str, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Insert a single row; returns inserted row when possible.

    If Supabase is not configured, logs and returns None.
    """
    sb = _client()
    if not sb:
        logger.info(f"supabase_insert skipped (no supabase): table={table}")
        return None
    try:
        # python-supabase v2 style
        res = sb.table(table).insert(record).execute()
        return getattr(res, "data", None)
    except Exception as e:
        logger.warning(f"Supabase insert failed for {table}: {e}")
        return None


def supabase_select_one(table: str, *, eq: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Select first row matching equals filters. Returns dict or None."""
    sb = _client()
    if not sb:
        logger.info(f"supabase_select_one skipped (no supabase): table={table}")
        return None


def supabase_select(table: str, *, limit: int = 100) -> Optional[List[Dict[str, Any]]]:
    """Select rows from a table (best-effort). Returns list or None if unavailable."""
    sb = _client()
    if not sb:
        logger.info(f"supabase_select skipped (no supabase): table={table}")
        return None
    try:
        res = sb.table(table).select("*").limit(limit).execute()
        return getattr(res, "data", [])
    except Exception as e:
        logger.warning(f"Supabase select failed for {table}: {e}")
        return None
    try:
        q = sb.table(table).select("*")
        for k, v in eq.items():
            q = q.eq(k, v)
        res = q.limit(1).execute()
        data = getattr(res, "data", [])
        return data[0] if data else None
    except Exception as e:
        logger.warning(f"Supabase select failed for {table}: {e}")
        return None
