import json
import logging
import os
from typing import Any, Dict, Optional

try:
    import boto3
    from botocore.exceptions import ClientError, BotoCoreError
    HAS_S3 = True
except ImportError:
    HAS_S3 = False

try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False
    class Client: pass

logger = logging.getLogger(__name__)

class StorageError(Exception):
    pass

def get_storage_backend() -> str:
    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY"):
        return "supabase"
    elif os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("S3_BUCKET"):
        return "s3"
    return "supabase"

def get_supabase_client() -> Client:
    if not HAS_SUPABASE:
        raise StorageError("Supabase client not available. pip install supabase")
    url = os.getenv("SUPABASE_URL"); key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_ROLE")
    if not url or not key:
        raise StorageError("SUPABASE_URL and SUPABASE_(ANON_KEY or SERVICE_ROLE) required")
    return create_client(url, key)

def get_s3_client():
    if not HAS_S3:
        raise StorageError("boto3 not available. pip install boto3")
    return boto3.client("s3")

def _has_path_traversal(path: str) -> bool:
    dangerous = ["..","//","./","\","%2e%2e","%2f%2f"]
    p = path.lower()
    return any(x in p for x in dangerous)

class UnifiedStorage:
    def __init__(self, bucket: str):
        self.bucket = bucket
        self.backend = get_storage_backend()
        self.client = get_supabase_client() if self.backend == "supabase" else get_s3_client()

    def put_object(self, key: str, data: bytes, content_type: str, public: bool=False,
                   metadata: Optional[Dict[str,str]]=None, cache_control: Optional[str]=None) -> None:
        if _has_path_traversal(key):
            raise ValueError(f"Path traversal: {key}")
        if self.backend == "supabase":
            res = self.client.storage.from_(self.bucket).upload(
                path=key, file=data,
                file_options={"content-type": content_type,
                              "cache-control": "31536000" if public else "3600"}
            )
            if hasattr(res, "error") and res.error:
                raise StorageError(f"Supabase upload failed: {res.error}")
        else:
            params = {"Bucket": self.bucket, "Key": key, "Body": data, "ContentType": content_type}
            if "public" not in self.bucket.lower():
                params["ServerSideEncryption"] = "AES256"
            if metadata: params["Metadata"] = metadata
            if cache_control: params["CacheControl"] = cache_control
            self.client.put_object(**params)

    def get_public_url(self, key: str, expires: int=3600) -> str:
        if self.backend == "supabase":
            # Try signed URL first
            res = self.client.storage.from_(self.bucket).create_signed_url(key, expires)
            if res and hasattr(res, "signedURL"):
                return res.signedURL
            # Fallback public URL
            return self.client.storage.from_(self.bucket).get_public_url(key)
        else:
            return self.client.generate_presigned_url(
                "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=expires
            )

    def object_exists(self, key: str) -> bool:
        if self.backend == "supabase":
            prefix = key.rsplit("/",1)[0] if "/" in key else ""
            listing = self.client.storage.from_(self.bucket).list(path=prefix, limit=1000)
            if hasattr(listing, "error") and listing.error: return False
            name = key.split("/")[-1]
            data = getattr(listing, "data", listing) or []
            return any(item.get("name")==name for item in data)
        else:
            try:
                self.client.head_object(Bucket=self.bucket, Key=key)
                return True
            except Exception:
                return False

def write_json(bucket: str, key: str, obj: Any, public: bool=False, cache_control: Optional[str]=None) -> None:
    data = json.dumps(obj, indent=2).encode("utf-8")
    UnifiedStorage(bucket).put_object(key, data, "application/json", public=public, cache_control=cache_control)
