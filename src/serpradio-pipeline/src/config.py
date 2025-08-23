import os
from dataclasses import dataclass

@dataclass
class Settings:
    openai_api_key: str = os.environ.get("OPENAI_API_KEY","")
    supabase_url: str = os.environ.get("SUPABASE_URL","")
    supabase_key: str = os.environ.get("SUPABASE_SERVICE_ROLE") or os.environ.get("SUPABASE_ANON_KEY","")
    tequila_key: str = os.environ.get("TEQUILA_API_KEY","")
    public_bucket: str = os.environ.get("PUBLIC_BUCKET","serpradio-public-2025")
    artifacts_bucket: str = os.environ.get("ARTIFACTS_BUCKET","serpradio-artifacts-2025")
    public_cdn_domain: str = os.environ.get("PUBLIC_CDN_DOMAIN","")
    tenant: str = os.environ.get("TENANT","serpradio")
    region: str = os.environ.get("AWS_REGION","us-east-1")

    def assert_minimum(self):
        missing = []
        if not self.supabase_url: missing.append("SUPABASE_URL")
        if not self.supabase_key: missing.append("SUPABASE_SERVICE_ROLE (or SUPABASE_ANON_KEY)")
        if missing:
            raise RuntimeError(f"Missing required environment vars: {', '.join(missing)}")
        return True

settings = Settings()
