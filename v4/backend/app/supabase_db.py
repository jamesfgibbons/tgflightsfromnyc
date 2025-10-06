from __future__ import annotations
import os
from supabase import create_client


def get_client():
    url = os.getenv("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )
    if not (url and key):
        raise RuntimeError("Supabase not configured: set SUPABASE_URL and SERVICE_ROLE/ANON key")
    return create_client(url, key)
