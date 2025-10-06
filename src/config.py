"""Shared settings module for SERP Radio pipelines and API."""
from __future__ import annotations
import os
from dataclasses import dataclass


@dataclass
class Settings:
    supabase_url: str = os.environ.get("SUPABASE_URL", "")
    supabase_key: str = (
        os.environ.get("SUPABASE_SERVICE_ROLE")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_ANON_KEY", "")
    )
    openai_api_key: str = os.environ.get("OPENAI_API_KEY", "")
    tequila_api_key: str = os.environ.get("TEQUILA_API_KEY", "")
    artifacts_bucket: str = os.environ.get("STORAGE_BUCKET") or os.environ.get("S3_BUCKET", "serpradio-artifacts")
    public_bucket: str = os.environ.get("PUBLIC_STORAGE_BUCKET") or os.environ.get("S3_PUBLIC_BUCKET", artifacts_bucket)
    public_cdn_domain: str = os.environ.get("PUBLIC_CDN_DOMAIN", "")
    tenant: str = os.environ.get("TENANT", "serpradio")
    region: str = os.environ.get("AWS_REGION", "us-east-1")

    def assert_minimum(self) -> bool:
        missing = []
        if not self.supabase_url:
            missing.append("SUPABASE_URL")
        if not self.supabase_key:
            missing.append("SUPABASE_SERVICE_ROLE (or SUPABASE_ANON_KEY)")
        if missing:
            raise RuntimeError(f"Missing required environment vars: {', '.join(missing)}")
        return True


settings = Settings()

