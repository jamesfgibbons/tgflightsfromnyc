"""
Unit tests for storage operations.
"""

import pytest
from moto import mock_aws
import boto3

from src.storage import (
    put_bytes, get_presigned_url, ensure_tenant_prefix, 
    write_json, read_text_s3, object_exists, StorageError
)


@pytest.fixture
def mock_s3_setup():
    """Set up mocked S3 environment."""
    with mock_aws():
        s3_client = boto3.client("s3", region_name="us-east-1")
        bucket_name = "test-bucket"
        s3_client.create_bucket(Bucket=bucket_name)
        yield s3_client, bucket_name


class TestS3Operations:
    """Test basic S3 operations."""
    
    def test_put_bytes(self, mock_s3_setup):
        """Test uploading bytes to S3."""
        s3_client, bucket_name = mock_s3_setup
        
        test_data = b"test content"
        key = "test/file.txt"
        
        put_bytes(bucket_name, key, test_data, "text/plain")
        
        # Verify object exists
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        assert response["Body"].read() == test_data
        assert response["ContentType"] == "text/plain"
    
    def test_get_presigned_url(self, mock_s3_setup):
        """Test generating presigned URLs."""
        s3_client, bucket_name = mock_s3_setup
        
        # Upload test object
        key = "test/file.txt" 
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=b"test")
        
        url = get_presigned_url(bucket_name, key, expires=3600)
        
        assert isinstance(url, str)
        assert bucket_name in url
        assert key in url
    
    def test_write_json(self, mock_s3_setup):
        """Test writing JSON to S3."""
        s3_client, bucket_name = mock_s3_setup
        
        test_data = {"key": "value", "number": 42}
        key = "test/data.json"
        
        write_json(bucket_name, key, test_data)
        
        # Verify JSON was stored correctly
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        stored_data = response["Body"].read().decode("utf-8")
        assert '"key": "value"' in stored_data
        assert '"number": 42' in stored_data
    
    def test_read_text_s3(self, mock_s3_setup):
        """Test reading text from S3."""
        s3_client, bucket_name = mock_s3_setup
        
        test_content = "Hello, world!"
        key = "test/file.txt"
        
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=test_content.encode())
        
        s3_uri = f"s3://{bucket_name}/{key}"
        content = read_text_s3(s3_uri)
        
        assert content == test_content
    
    def test_object_exists(self, mock_s3_setup):
        """Test checking object existence."""
        s3_client, bucket_name = mock_s3_setup
        
        existing_key = "test/exists.txt"
        missing_key = "test/missing.txt"
        
        # Create one object
        s3_client.put_object(Bucket=bucket_name, Key=existing_key, Body=b"test")
        
        assert object_exists(bucket_name, existing_key) is True
        assert object_exists(bucket_name, missing_key) is False


class TestTenantPrefix:
    """Test tenant path handling."""
    
    def test_ensure_tenant_prefix_basic(self):
        """Test basic tenant prefix creation."""
        result = ensure_tenant_prefix("acme", "midi_input", "file.mid")
        assert result == "acme/midi_input/file.mid"
    
    def test_ensure_tenant_prefix_single_part(self):
        """Test tenant prefix with single part."""
        result = ensure_tenant_prefix("acme", "file.mid")
        assert result == "acme/file.mid"
    
    def test_ensure_tenant_prefix_multiple_parts(self):
        """Test tenant prefix with many parts."""
        result = ensure_tenant_prefix("acme", "logs", "2024", "01", "file.json")
        assert result == "acme/logs/2024/01/file.json"
    
    def test_ensure_tenant_prefix_path_traversal(self):
        """Test path traversal protection."""
        with pytest.raises(ValueError, match="Path traversal detected"):
            ensure_tenant_prefix("acme", "..", "file.txt")
        
        with pytest.raises(ValueError, match="Invalid tenant"):
            ensure_tenant_prefix("../bad", "file.txt")


class TestSecurityValidation:
    """Test security validation."""
    
    def test_path_traversal_prevention(self, mock_s3_setup):
        """Test path traversal attack prevention."""
        s3_client, bucket_name = mock_s3_setup
        
        dangerous_keys = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "%2e%2e/sensitive", 
            "//double/slash"
        ]
        
        for key in dangerous_keys:
            with pytest.raises(ValueError, match="Path traversal detected"):
                put_bytes(bucket_name, key, b"test", "text/plain")
    
    def test_invalid_s3_uri(self):
        """Test invalid S3 URI handling."""
        with pytest.raises(ValueError, match="Invalid S3 URI"):
            read_text_s3("http://not-s3.com/file.txt")
        
        with pytest.raises(ValueError, match="Invalid S3 URI"):
            read_text_s3("s3://")
    
    def test_nonexistent_file_read(self, mock_s3_setup):
        """Test reading non-existent file."""
        s3_client, bucket_name = mock_s3_setup
        
        with pytest.raises(StorageError, match="File not found"):
            read_text_s3(f"s3://{bucket_name}/missing/file.txt")