"""
Unit tests for storage presigned URL functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
import boto3
from moto import mock_aws
from src.storage import S3Storage, get_presigned_url


@mock_aws
class TestPresignedURLs:
    """Test presigned URL generation with and without force download."""
    
    def setup_method(self):
        """Set up S3 mock environment for each test."""
        self.bucket_name = "test-bucket"
        self.s3_client = boto3.client("s3", region_name="us-east-1")
        self.s3_client.create_bucket(Bucket=self.bucket_name)
        
    def test_generate_presigned_url_default_no_download(self):
        """Test that presigned URLs don't force download by default."""
        storage = S3Storage(self.bucket_name)
        
        # Put a test object
        test_key = "test/audio.mp3"
        self.s3_client.put_object(Bucket=self.bucket_name, Key=test_key, Body=b"test content")
        
        # Generate presigned URL with default settings
        url = storage.generate_presigned_url(test_key, expiration=3600)
        
        # URL should not contain response-content-disposition
        assert "response-content-disposition" not in url.lower()
        assert "attachment" not in url.lower()
        
    def test_generate_presigned_url_force_download_false(self):
        """Test presigned URL with force_download explicitly set to False."""
        storage = S3Storage(self.bucket_name)
        
        test_key = "test/music.mp3"
        self.s3_client.put_object(Bucket=self.bucket_name, Key=test_key, Body=b"audio data")
        
        url = storage.generate_presigned_url(test_key, expiration=3600, force_download=False)
        
        # Should not contain download headers
        assert "response-content-disposition" not in url.lower()
        
    def test_generate_presigned_url_force_download_true(self):
        """Test presigned URL with force_download set to True."""
        storage = S3Storage(self.bucket_name)
        
        test_key = "test/document.pdf"
        self.s3_client.put_object(Bucket=self.bucket_name, Key=test_key, Body=b"pdf content")
        
        url = storage.generate_presigned_url(test_key, expiration=3600, force_download=True)
        
        # Should contain download headers
        assert "response-content-disposition" in url.lower()
        assert "attachment" in url.lower()
        
    def test_legacy_get_presigned_url_function(self):
        """Test the legacy get_presigned_url function with new parameters."""
        test_key = "legacy/test.mp3"
        self.s3_client.put_object(Bucket=self.bucket_name, Key=test_key, Body=b"legacy content")
        
        # Test default behavior (no force download)
        url = get_presigned_url(self.bucket_name, test_key)
        assert "response-content-disposition" not in url.lower()
        
        # Test with force_download=False
        url = get_presigned_url(self.bucket_name, test_key, force_download=False)
        assert "response-content-disposition" not in url.lower()
        
        # Test with force_download=True
        url = get_presigned_url(self.bucket_name, test_key, force_download=True)
        assert "response-content-disposition" in url.lower()
        assert "attachment" in url.lower()
        
    def test_presigned_url_expiration_parameter(self):
        """Test that expiration parameter is respected."""
        storage = S3Storage(self.bucket_name)
        
        test_key = "test/expire.mp3"
        self.s3_client.put_object(Bucket=self.bucket_name, Key=test_key, Body=b"expire test")
        
        # Generate URL with custom expiration
        url = storage.generate_presigned_url(test_key, expiration=7200)  # 2 hours
        
        # URL should be generated (basic validation)
        assert f"/{test_key}" in url
        assert self.bucket_name in url
        
    def test_presigned_url_path_traversal_protection(self):
        """Test that path traversal is prevented in presigned URLs."""
        storage = S3Storage(self.bucket_name)
        
        # Test various path traversal attempts
        malicious_keys = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32",
            "test/../../../secret",
            "./test/../hidden"
        ]
        
        for key in malicious_keys:
            with pytest.raises(ValueError, match="Path traversal detected"):
                storage.generate_presigned_url(key)
                
    def test_presigned_url_different_file_types(self):
        """Test presigned URLs for different file types with appropriate settings."""
        storage = S3Storage(self.bucket_name)
        
        # Audio files - should not force download
        audio_files = ["music.mp3", "song.wav", "audio.m4a"]
        for file_key in audio_files:
            self.s3_client.put_object(Bucket=self.bucket_name, Key=file_key, Body=b"audio")
            url = storage.generate_presigned_url(file_key, force_download=False)
            assert "response-content-disposition" not in url.lower()
            
        # MIDI files - should not force download
        midi_files = ["composition.mid", "sequence.midi"]
        for file_key in midi_files:
            self.s3_client.put_object(Bucket=self.bucket_name, Key=file_key, Body=b"midi")
            url = storage.generate_presigned_url(file_key, force_download=False) 
            assert "response-content-disposition" not in url.lower()
            
        # Documents that should force download when requested
        doc_files = ["report.pdf", "data.csv", "config.json"]
        for file_key in doc_files:
            self.s3_client.put_object(Bucket=self.bucket_name, Key=file_key, Body=b"document")
            url = storage.generate_presigned_url(file_key, force_download=True)
            assert "response-content-disposition" in url.lower()
            assert "attachment" in url.lower()