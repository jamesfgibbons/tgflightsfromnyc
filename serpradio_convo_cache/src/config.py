import os
from dataclasses import dataclass

@dataclass
class Settings:
    # API keys
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_SERVICE_ROLE") or os.getenv("SUPABASE_ANON_KEY", "")
    search_api_key: str = os.getenv("TAVILY_API_KEY") or os.getenv("BRAVE_API_KEY") or os.getenv("SERPAPI_API_KEY", "")

    # Model & runtime
    model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature: float = float(os.getenv("OPENAI_TEMP", "0.2"))
    max_output_tokens: int = int(os.getenv("OPENAI_MAX_TOKENS", "700"))
    mock: bool = os.getenv("OPENAI_MOCK", "0") == "1"

    # Batch & theme
    batch_size: int = int(os.getenv("BATCH_SIZE", "8"))
    region: str = os.getenv("REGION", "caribbean")
    run_id: str = os.getenv("RUN_ID", "")  # optional; will be auto-generated if empty

    def assert_minimum(self):
        if not self.supabase_url or not self.supabase_key:
            raise RuntimeError("Missing SUPABASE_URL / SUPABASE_SERVICE_ROLE (or ANON for read-only).")
        if not self.openai_api_key and not self.mock:
            raise RuntimeError("Missing OPENAI_API_KEY (or set OPENAI_MOCK=1 to dry-run).")

settings = Settings()
