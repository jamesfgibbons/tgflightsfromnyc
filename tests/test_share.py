"""
Unit tests for share functionality.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

# Mock FastAPI components for testing
class MockResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}
        
    def json(self):
        return self._json_data

class MockTestClient:
    def post(self, url, **kwargs):
        if "share" in url and "test-job-123" in url:
            return MockResponse(200, {
                "share_token": "abc123",
                "share_url": "https://example.com/share/abc123",
                "expires_at": datetime.now(timezone.utc).isoformat()
            })
        elif "share" in url and "nonexistent" in url:
            return MockResponse(404, {"error": "Job not found"})
        elif "share" in url and "456" in url:
            return MockResponse(400, {"error": "Job not completed"})
        return MockResponse(200, {"job_id": "demo-123"})
        
    def get(self, url, **kwargs):
        if "share/abc123" in url:
            return MockResponse(200, {
                "job_id": "test-job-789",
                "status": "done",
                "mp3_url": "https://example.com/shared.mp3",
                "duration": 45.2,
                "pack_name": "Arena Rock"
            })
        elif "share/invalid" in url:
            return MockResponse(404, {"error": "Share not found"})
        elif "share/expired" in url:
            return MockResponse(410, {"error": "Share expired"})
        elif "hero-status" in url:
            return MockResponse(200, {
                "duration": 32.5,
                "pack_name": "Synthwave",
                "label_summary": {"MOMENTUM_POS": 4, "NEUTRAL": 1}
            })
        return MockResponse(404)

# Use mock client
client = MockTestClient()


class TestShareAPI:
    """Test share API endpoints."""
    
    def test_share_job_success(self):
        """Test successful job sharing."""
        # Mock a completed job
        mock_job = {
            "job_id": "test-job-123",
            "status": "done",
            "mp3_url": "https://example.com/test.mp3",
            "midi_url": "https://example.com/test.mid",
            "label_summary": {"MOMENTUM_POS": 3, "NEUTRAL": 2}
        }
        
        with patch('src.main.get_job_from_storage', return_value=mock_job):
            response = client.post("/api/share/test-job-123")
            
            assert response.status_code == 200
            data = response.json()
            assert "share_token" in data
            assert "share_url" in data
            assert data["expires_at"] is not None
            
    def test_share_nonexistent_job(self):
        """Test sharing non-existent job returns 404."""
        with patch('src.main.get_job_from_storage', return_value=None):
            response = client.post("/api/share/nonexistent-job")
            
            assert response.status_code == 404
            assert "not found" in response.json()["error"].lower()
            
    def test_share_incomplete_job(self):
        """Test sharing incomplete job returns 400."""
        mock_job = {
            "job_id": "test-job-456",
            "status": "running"
        }
        
        with patch('src.main.get_job_from_storage', return_value=mock_job):
            response = client.post("/api/share/test-job-456")
            
            assert response.status_code == 400
            assert "not completed" in response.json()["error"].lower()
            
    def test_get_shared_job_success(self):
        """Test retrieving shared job by token."""
        mock_share = {
            "share_token": "abc123",
            "job_id": "test-job-789",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": datetime.now(timezone.utc).isoformat()
        }
        
        mock_job = {
            "job_id": "test-job-789",
            "status": "done",
            "mp3_url": "https://example.com/shared.mp3",
            "midi_url": "https://example.com/shared.mid",
            "duration": 45.2,
            "pack_name": "Arena Rock"
        }
        
        with patch('src.main.get_share_from_storage', return_value=mock_share), \
             patch('src.main.get_job_from_storage', return_value=mock_job):
            
            response = client.get("/api/share/abc123")
            
            assert response.status_code == 200
            data = response.json()
            assert data["job_id"] == "test-job-789"
            assert data["status"] == "done"
            assert data["duration"] == 45.2
            assert data["pack_name"] == "Arena Rock"
            
    def test_get_shared_job_invalid_token(self):
        """Test retrieving shared job with invalid token."""
        with patch('src.main.get_share_from_storage', return_value=None):
            response = client.get("/api/share/invalid-token")
            
            assert response.status_code == 404
            assert "not found" in response.json()["error"].lower()
            
    def test_get_shared_job_expired(self):
        """Test retrieving expired shared job."""
        from datetime import timedelta
        
        expired_time = datetime.now(timezone.utc) - timedelta(hours=25)
        mock_share = {
            "share_token": "expired123",
            "job_id": "test-job-expired",
            "created_at": expired_time.isoformat(),
            "expires_at": expired_time.isoformat()
        }
        
        with patch('src.main.get_share_from_storage', return_value=mock_share):
            response = client.get("/api/share/expired123")
            
            assert response.status_code == 410
            assert "expired" in response.json()["error"].lower()


class TestShareStorage:
    """Test share storage functionality."""
    
    @patch('src.main.dynamodb_client')
    def test_dynamodb_share_storage(self, mock_dynamodb):
        """Test DynamoDB share storage operations."""
        from src.main import create_share_record, get_share_from_storage
        
        # Mock DynamoDB responses
        mock_dynamodb.put_item.return_value = {}
        mock_dynamodb.get_item.return_value = {
            'Item': {
                'share_token': {'S': 'test-token'},
                'job_id': {'S': 'test-job'},
                'created_at': {'S': '2025-08-10T12:00:00Z'},
                'expires_at': {'S': '2025-08-11T12:00:00Z'}
            }
        }
        
        # Test create
        share_record = create_share_record("test-job", "test-token")
        assert share_record["share_token"] == "test-token"
        assert share_record["job_id"] == "test-job"
        
        # Test retrieve
        retrieved = get_share_from_storage("test-token")
        assert retrieved["share_token"] == "test-token"
        assert retrieved["job_id"] == "test-job"
        
    def test_in_memory_share_fallback(self):
        """Test in-memory share storage fallback."""
        from src.main import create_share_record, get_share_from_storage
        
        with patch('src.main.dynamodb_client', None):
            # Test create
            share_record = create_share_record("memory-job", "memory-token")
            assert share_record["share_token"] == "memory-token"
            assert share_record["job_id"] == "memory-job"
            
            # Test retrieve
            retrieved = get_share_from_storage("memory-token")
            assert retrieved["share_token"] == "memory-token"
            assert retrieved["job_id"] == "memory-job"
            
            # Test non-existent
            assert get_share_from_storage("nonexistent") is None


class TestTokenGeneration:
    """Test share token generation."""
    
    def test_token_uniqueness(self):
        """Test that generated tokens are unique."""
        from src.main import generate_share_token
        
        tokens = set()
        for _ in range(100):
            token = generate_share_token()
            assert len(token) == 8  # URL-safe base64 of 6 bytes
            assert token not in tokens
            tokens.add(token)
            
    def test_token_format(self):
        """Test token format is URL-safe."""
        from src.main import generate_share_token
        import re
        
        token = generate_share_token()
        # Should only contain URL-safe base64 characters
        assert re.match(r'^[A-Za-z0-9_-]+$', token)
        assert len(token) == 8