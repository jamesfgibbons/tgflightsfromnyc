"""
Unit tests for Supabase storage operations.
"""
import pytest
from unittest.mock import Mock, patch

from src.storage import (
    UnifiedStorage, put_bytes, get_presigned_url, ensure_tenant_prefix, 
    write_json, object_exists, StorageError
)


class TestSupabaseStorage:
    """Test Supabase storage operations."""
    
    def test_put_bytes(self):
        """Test uploading bytes to Supabase."""
        # Use UnifiedStorage directly
        storage = UnifiedStorage("test-bucket")
        storage.backend = "supabase"
        
        test_data = b"test content"
        key = "test/file.txt"
        
        storage.put_object(key, test_data, "text/plain")
        
        # Verify the upload was called correctly
        storage.client.storage.from_.assert_called_with("test-bucket")
        mock_bucket = storage.client.storage.from_.return_value
        mock_bucket.upload.assert_called_once()
        
        # Check the upload parameters
        upload_call = mock_bucket.upload.call_args
        assert upload_call[1]['path'] == key
        assert upload_call[1]['file'] == test_data
        assert upload_call[1]['file_options']['content-type'] == "text/plain"
    
    def test_get_presigned_url(self):
        """Test generating presigned URLs from Supabase."""
        storage = UnifiedStorage("test-bucket")
        storage.backend = "supabase"
        
        key = "test/file.txt"
        url = storage.get_presigned_url(key, expires=3600)
        
        # Verify URL generation was called
        mock_bucket = storage.client.storage.from_.return_value
        mock_bucket.create_signed_url.assert_called_once()
        
        assert url == "https://test.supabase.co/storage/v1/object/sign/test-bucket/test-key"
    
    def test_object_exists(self):
        """Test checking if object exists in Supabase."""
        storage = UnifiedStorage("test-bucket")
        storage.backend = "supabase"
        
        # Mock list response to indicate object exists
        mock_bucket = storage.client.storage.from_.return_value
        mock_list_response = Mock()
        mock_list_response.error = None
        mock_list_response.data = [{"name": "file.txt"}]
        mock_bucket.list.return_value = mock_list_response
        
        exists = storage.object_exists("test/file.txt")
        assert exists is True
        
        # Test non-existent object
        mock_list_response.data = []
        exists = storage.object_exists("test/missing.txt")
        assert exists is False
    
    def test_path_traversal_protection(self):
        """Test that path traversal attempts are blocked."""
        storage = UnifiedStorage("test-bucket")
        storage.backend = "supabase"
        
        # Test various path traversal attempts
        bad_keys = [
            "../etc/passwd",
            "../../sensitive.txt",
            "test/../../../etc/passwd",
            "test/..\\..\\windows\\system32"
        ]
        
        for bad_key in bad_keys:
            with pytest.raises(ValueError, match="Path traversal detected"):
                storage.put_object(bad_key, b"malicious", "text/plain")
    
    def test_tenant_prefix(self):
        """Test tenant prefix functionality."""
        assert ensure_tenant_prefix("tenant123", "file.txt") == "tenant123/file.txt"
        assert ensure_tenant_prefix("tenant123", "subfolder", "file.txt") == "tenant123/subfolder/file.txt"
        assert ensure_tenant_prefix("tenant123", "other/file.txt") == "tenant123/other/file.txt"