"""
Storage operations for SERP Radio - supports both S3 and Supabase Storage.
"""

import json
import logging
import os
from typing import Any, Dict, Optional
from urllib.parse import urlparse

# Try importing both S3 and Supabase clients
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
    # Create dummy type for type hints when Supabase not available
    class Client:
        pass

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Custom exception for storage operations."""
    pass


def get_storage_backend() -> str:
    """Determine which storage backend to use based on environment.

    Prefer Supabase when either ANON or SERVICE_ROLE is configured.
    """
    if os.getenv("SUPABASE_URL") and (os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_SERVICE_ROLE") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")):
        return "supabase"
    elif os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("S3_BUCKET"):
        return "s3"
    else:
        # Default to S3/local mocks when no env hints are provided
        return "s3"


def get_supabase_client() -> Client:
    """Get configured Supabase client.

    Uses SERVICE_ROLE key if present (server-side), else falls back to ANON key.
    """
    if not HAS_SUPABASE:
        raise StorageError("Supabase client not available. Install with: pip install supabase")
    
    url = os.getenv("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )
    
    if not url or not key:
        raise StorageError("SUPABASE_URL and either SUPABASE_SERVICE_ROLE(_KEY) or SUPABASE_ANON_KEY required")
    
    try:
        return create_client(url, key)
    except Exception as e:
        raise StorageError(f"Failed to create Supabase client: {e}")


def get_s3_client():
    """Get configured S3 client."""
    if not HAS_S3:
        raise StorageError("S3 client not available. Install with: pip install boto3")
    try:
        return boto3.client("s3")
    except Exception as e:
        raise StorageError(f"Failed to create S3 client: {e}")


class UnifiedStorage:
    """Unified storage interface supporting both S3 and Supabase."""
    
    def __init__(self, bucket: str):
        self.bucket = bucket
        self.backend = get_storage_backend()
        
        if self.backend == "supabase":
            self.client = get_supabase_client()
        else:
            self.client = get_s3_client()
    
    def put_object(self, key: str, data: bytes, content_type: str, 
                   metadata: Optional[Dict[str, str]] = None, 
                   cache_control: Optional[str] = None,
                   public: bool = False) -> None:
        """Upload object with unified interface."""
        if _has_path_traversal(key):
            raise ValueError(f"Path traversal detected in key: {key}")
        
        if self.backend == "supabase":
            self._put_supabase(key, data, content_type, public)
        else:
            self._put_s3(key, data, content_type, metadata, cache_control)
    
    def _put_supabase(self, key: str, data: bytes, content_type: str, public: bool = False) -> None:
        """Upload to Supabase Storage with proper error handling."""
        try:
            # Ensure data is bytes (critical for Supabase upload)
            if not isinstance(data, bytes):
                raise ValueError(f"Data must be bytes, got {type(data)}")
            
            # Supabase storage upload (use camelCase keys)
            result = self.client.storage.from_(self.bucket).upload(
                path=key,
                file=data,
                file_options={
                    "contentType": content_type,
                    "cacheControl": "3600" if not public else "31536000",
                    "upsert": "true",
                }
            )
            
            # Check for errors - result might be a dict or object
            if hasattr(result, 'error') and result.error:
                raise StorageError(f"Supabase upload failed: {result.error}")
            elif isinstance(result, dict) and result.get('error'):
                raise StorageError(f"Supabase upload failed: {result['error']}")
            
            logger.info(f"Uploaded {len(data)} bytes to supabase://{self.bucket}/{key}")
        except StorageError:
            raise
        except Exception as e:
            raise StorageError(f"Failed to upload to Supabase: {e}")
    
    def _put_s3(self, key: str, data: bytes, content_type: str, 
                metadata: Optional[Dict[str, str]] = None, 
                cache_control: Optional[str] = None) -> None:
        """Upload to S3."""
        try:
            put_params = {
                "Bucket": self.bucket,
                "Key": key,
                "Body": data,
                "ContentType": content_type
            }
            
            if "public" not in self.bucket.lower():
                put_params["ServerSideEncryption"] = "AES256"
            
            if metadata:
                put_params["Metadata"] = metadata
                
            if cache_control:
                put_params["CacheControl"] = cache_control
                
            self.client.put_object(**put_params)
            logger.info(f"Uploaded {len(data)} bytes to s3://{self.bucket}/{key}")
        except Exception as e:
            raise StorageError(f"Failed to upload to S3: {e}")
    
    def get_public_url(self, key: str, expires: int = 3600) -> str:
        """Get public URL for object."""
        if _has_path_traversal(key):
            raise ValueError(f"Path traversal detected in key: {key}")
        
        if self.backend == "supabase":
            return self._get_supabase_url(key)
        else:
            return self._get_s3_presigned_url(key, expires)
    
    def get_presigned_url(self, key: str, expires: int = 3600) -> str:
        """Get presigned URL for object (alias for get_public_url)."""
        return self.get_public_url(key, expires)
    
    def _get_supabase_url(self, key: str) -> str:
        """Get Supabase public URL."""
        try:
            # Try to get signed URL for better security
            result = self.client.storage.from_(self.bucket).create_signed_url(key, 3600)
            if result and hasattr(result, 'signedURL'):
                return result.signedURL
            
            # Fallback to public URL
            result = self.client.storage.from_(self.bucket).get_public_url(key)
            if not result:
                raise StorageError(f"Failed to get Supabase public URL for {key}")
            return result
        except Exception as e:
            raise StorageError(f"Failed to get Supabase URL: {e}")
    
    def _get_s3_presigned_url(self, key: str, expires: int) -> str:
        """Get S3 presigned URL."""
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires
            )
            return url
        except Exception as e:
            raise StorageError(f"Failed to generate S3 presigned URL: {e}")
    
    def object_exists(self, key: str) -> bool:
        """Check if object exists."""
        if _has_path_traversal(key):
            raise ValueError(f"Path traversal detected in key: {key}")
        
        if self.backend == "supabase":
            return self._supabase_exists(key)
        else:
            return self._s3_exists(key)
    
    def _supabase_exists(self, key: str) -> bool:
        """Check if object exists in Supabase."""
        try:
            # List files to check existence
            result = self.client.storage.from_(self.bucket).list(
                path=key.rsplit('/', 1)[0] if '/' in key else '',
                limit=1000
            )
            
            if result.error:
                return False
            
            # Check if our file is in the list
            filename = key.split('/')[-1]
            return any(file.get('name') == filename for file in result.data)
        except Exception:
            return False
    
    def _s3_exists(self, key: str) -> bool:
        """Check if object exists in S3."""
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False


def put_bytes(bucket: str, key: str, data: bytes, content_type: str, public: bool = False) -> None:
    """
    Upload bytes using unified storage interface.
    
    Args:
        bucket: Storage bucket/container name
        key: Object key/path
        data: Bytes to upload
        content_type: MIME content type
        public: Whether this should be publicly accessible
    
    Raises:
        StorageError: If upload fails
    """
    storage = UnifiedStorage(bucket)
    storage.put_object(key, data, content_type, public=public)


class S3Storage:
    """S3 storage operations with enhanced features."""
    
    def __init__(self, bucket: str):
        self.bucket = bucket
        self.s3_client = get_s3_client()
    
    def head_object(self, key: str) -> Dict[str, Any]:
        """
        Get object metadata without downloading the object.
        
        Args:
            key: S3 object key
            
        Returns:
            Object metadata dictionary
            
        Raises:
            StorageError: If object doesn't exist or other error
        """
        if _has_path_traversal(key):
            raise ValueError(f"Path traversal detected in key: {key}")
            
        try:
            response = self.s3_client.head_object(Bucket=self.bucket, Key=key)
            return response
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise StorageError(f"Object not found: s3://{self.bucket}/{key}")
            raise StorageError(f"Failed to get object metadata: {e}")
    
    def generate_presigned_url(self, key: str, expiration: int = 3600, force_download: bool = False) -> str:
        """
        Generate presigned URL for S3 object.
        
        Args:
            key: S3 object key
            expiration: URL expiration time in seconds
            force_download: If True, force download with Content-Disposition header
        
        Returns:
            Presigned URL string
        
        Raises:
            StorageError: If URL generation fails
        """
        if _has_path_traversal(key):
            raise ValueError(f"Path traversal detected in key: {key}")
        
        try:
            params = {"Bucket": self.bucket, "Key": key}
            if force_download:
                params["ResponseContentDisposition"] = "attachment"
                
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params=params,
                ExpiresIn=expiration
            )
            logger.debug(f"Generated presigned URL for s3://{self.bucket}/{key} (expires in {expiration}s)")
            return url
        except (ClientError, BotoCoreError) as e:
            raise StorageError(f"Failed to generate presigned URL: {e}")
    
    def put_object(self, key: str, data: bytes, content_type: str, 
                   metadata: Dict[str, str] = None, cache_control: str = None) -> None:
        """
        Upload object to S3 with metadata and cache control.
        
        Args:
            key: S3 object key
            data: Bytes to upload
            content_type: MIME content type
            metadata: Optional metadata dictionary
            cache_control: Optional cache control header
            
        Raises:
            StorageError: If upload fails
        """
        if _has_path_traversal(key):
            raise ValueError(f"Path traversal detected in key: {key}")
            
        try:
            put_params = {
                "Bucket": self.bucket,
                "Key": key,
                "Body": data,
                "ContentType": content_type
            }
            
            # Only add encryption for private buckets
            # Public buckets should not use server-side encryption
            if "public" not in self.bucket.lower():
                put_params["ServerSideEncryption"] = "AES256"
            
            if metadata:
                put_params["Metadata"] = metadata
                
            if cache_control:
                put_params["CacheControl"] = cache_control
                
            self.s3_client.put_object(**put_params)
            logger.info(f"Uploaded {len(data)} bytes to s3://{self.bucket}/{key}")
        except (ClientError, BotoCoreError) as e:
            raise StorageError(f"Failed to upload to S3: {e}")


def get_presigned_url(bucket: str, key: str, expires: int = 3600, force_download: bool = False) -> str:
    """
    Generate presigned/public URL using unified storage interface.
    
    Args:
        bucket: Storage bucket name
        key: Object key
        expires: URL expiration time in seconds (ignored for Supabase)
        force_download: If True, force download (S3 only)
    
    Returns:
        Public or presigned URL string
    
    Raises:
        StorageError: If URL generation fails
    """
    storage = UnifiedStorage(bucket)
    return storage.get_public_url(key, expires)


def ensure_tenant_prefix(tenant: str, *parts: str) -> str:
    """
    Join path parts with tenant prefix, ensuring security.
    
    Args:
        tenant: Tenant identifier
        *parts: Path components to join
    
    Returns:
        Safe S3 key with tenant prefix
    
    Raises:
        ValueError: If path traversal detected
    """
    # Validate tenant
    if not tenant or "/" in tenant or ".." in tenant:
        raise ValueError(f"Invalid tenant identifier: {tenant}")
    
    # Join all parts
    all_parts = [tenant] + list(parts)
    key = "/".join(str(part).strip("/") for part in all_parts if part)
    
    # Security check
    if _has_path_traversal(key):
        raise ValueError(f"Path traversal detected: {key}")
    
    return key


def write_json(bucket: str, key: str, obj: Any, public: bool = False, cache_control: Optional[str] = None) -> None:
    """
    Write JSON object to storage.
    
    Args:
        bucket: Storage bucket name
        key: Object key
        obj: Object to serialize as JSON
        public: Whether this should be publicly accessible
        cache_control: Cache control header
    
    Raises:
        StorageError: If write fails
    """
    try:
        json_data = json.dumps(obj, indent=2).encode("utf-8")
        storage = UnifiedStorage(bucket)
        storage.put_object(key, json_data, "application/json", cache_control=cache_control, public=public)
    except (TypeError, ValueError) as e:
        raise StorageError(f"Failed to serialize JSON: {e}")


def read_text_s3(bucket: str, key: Optional[str] = None, public: bool = False) -> str:
    """
    Read text file from storage.

    Args:
        bucket: Storage bucket name or s3:// URI
        key: Object key (optional when bucket is s3:// URI)
        public: Whether reading from public storage

    Returns:
        File content as string

    Raises:
        StorageError: If read fails
    """
    original_bucket = bucket
    if key is None:
        if bucket.startswith("s3://"):
            parsed = urlparse(bucket)
            bucket = parsed.netloc
            key = parsed.path.lstrip("/")
        else:
            raise ValueError("Invalid S3 URI: key missing")

    if not key:
        raise ValueError(f"Invalid S3 URI: bucket={original_bucket} key={key}")

    backend = get_storage_backend()

    if backend == "supabase":
        return _read_supabase_text(bucket, key)
    else:
        return _read_s3_text(bucket, key)


def _read_supabase_text(bucket: str, key: str) -> str:
    """Read text from Supabase Storage."""
    try:
        client = get_supabase_client()
        result = client.storage.from_(bucket).download(key)
        
        if not result:
            raise StorageError(f"File not found: {bucket}/{key}")
        
        content = result.decode("utf-8")
        logger.debug(f"Read {len(content)} chars from supabase://{bucket}/{key}")
        return content
    except Exception as e:
        raise StorageError(f"Failed to read from Supabase: {e}")


def _read_s3_text(bucket: str, key: str) -> str:
    """Read text from S3."""
    try:
        # Security check
        if _has_path_traversal(key):
            raise ValueError(f"Path traversal detected in key: {key}")
        
        s3_client = get_s3_client()
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response["Body"].read().decode("utf-8")
        
        logger.debug(f"Read {len(content)} chars from s3://{bucket}/{key}")
        return content
        
    except (ClientError, BotoCoreError) as e:
        if hasattr(e, 'response') and e.response.get('Error', {}).get('Code') == 'NoSuchKey':
            raise StorageError(f"File not found: s3://{bucket}/{key}")
        raise StorageError(f"Failed to read from S3: {e}")
    except UnicodeDecodeError as e:
        raise StorageError(f"Failed to decode file content: {e}")


def object_exists(bucket: str, key: str) -> bool:
    """
    Check if object exists in storage.
    
    Args:
        bucket: Storage bucket name
        key: Object key
    
    Returns:
        True if object exists, False otherwise
    """
    storage = UnifiedStorage(bucket)
    return storage.object_exists(key)


def delete_object(bucket: str, key: str) -> bool:
    """
    Delete S3 object.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
    
    Returns:
        True if deleted successfully, False if object didn't exist
    
    Raises:
        StorageError: If delete operation fails
    """
    try:
        s3_client = get_s3_client()
        s3_client.delete_object(Bucket=bucket, Key=key)
        logger.info(f"Deleted s3://{bucket}/{key}")
        return True
    except (ClientError, BotoCoreError) as e:
        raise StorageError(f"Failed to delete S3 object: {e}")


def _has_path_traversal(path: str) -> bool:
    """
    Check for path traversal attempts.
    
    Args:
        path: Path to validate
    
    Returns:
        True if path traversal detected
    """
    dangerous_patterns = ["..", "//", "./", "\\", "%2e%2e", "%2f%2f"]
    path_lower = path.lower()
    
    return any(pattern in path_lower for pattern in dangerous_patterns)
