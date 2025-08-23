"""
Common test fixtures and configuration for SERP Radio tests.
"""
import os
import pytest
from unittest.mock import Mock, MagicMock
from io import BytesIO

# Set Supabase environment variables for testing
os.environ["SUPABASE_URL"] = "https://test.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "test-anon-key"
os.environ["STORAGE_BUCKET"] = "test-bucket"
os.environ["PUBLIC_STORAGE_BUCKET"] = "test-public-bucket"


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    mock_client = Mock()
    
    # Mock storage operations
    mock_storage = Mock()
    mock_bucket = Mock()
    
    # Mock upload response
    mock_upload_response = Mock()
    mock_upload_response.error = None
    mock_bucket.upload.return_value = mock_upload_response
    
    # Mock download response
    mock_download_response = Mock()
    mock_download_response.data = b"test data"
    mock_download_response.error = None
    mock_bucket.download.return_value = mock_download_response
    
    # Mock list response
    mock_list_response = Mock()
    mock_list_response.error = None
    mock_list_response.json.return_value = []
    mock_bucket.list.return_value = mock_list_response
    
    # Mock URL generation
    mock_url_response = Mock()
    mock_url_response.signedURL = "https://test.supabase.co/storage/v1/object/sign/test-bucket/test-key"
    mock_url_response.error = None
    mock_bucket.create_signed_url.return_value = mock_url_response
    
    # Chain the mocks
    mock_storage.from_.return_value = mock_bucket
    mock_client.storage = mock_storage
    
    return mock_client


@pytest.fixture(autouse=True)
def mock_supabase_import(monkeypatch, mock_supabase_client):
    """Mock the Supabase import and client creation."""
    mock_create_client = Mock(return_value=mock_supabase_client)
    
    # Mock the supabase module
    mock_supabase = Mock()
    mock_supabase.create_client = mock_create_client
    
    monkeypatch.setattr("src.storage.create_client", mock_create_client)
    monkeypatch.setattr("src.storage.HAS_SUPABASE", True)
    monkeypatch.setattr("src.storage.HAS_S3", False)
    
    return mock_create_client