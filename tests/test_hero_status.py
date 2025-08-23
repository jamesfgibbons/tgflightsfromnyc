"""
Unit tests for hero status endpoint.
"""

import pytest
from unittest.mock import patch, MagicMock
import os
from fastapi.testclient import TestClient
from src.main import app
from src.storage import StorageError


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_public_storage():
    with patch('src.main.S3Storage') as mock_s3_storage:
        yield mock_s3_storage


class TestHeroStatus:
    """Test hero status endpoint functionality."""
    
    def test_hero_status_object_exists_with_cdn(self, client, mock_public_storage):
        """Test hero status when object exists and CDN domain is configured."""
        # Mock storage instance
        mock_storage_instance = MagicMock()
        mock_public_storage.return_value = mock_storage_instance
        
        # Mock successful head_object response
        mock_storage_instance.head_object.return_value = {
            'Metadata': {'duration': '45.5'},
            'LastModified': '2025-01-01T00:00:00Z'
        }
        
        # Set environment variables
        with patch.dict(os.environ, {
            'S3_PUBLIC_BUCKET': 'test-public-bucket',
            'PUBLIC_CDN_DOMAIN': 'cdn.example.com'
        }):
            response = client.get("/api/hero-status")
            
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "packs" in data
        assert "Arena Rock" in data["packs"]
        
        arena_rock = data["packs"]["Arena Rock"]
        assert arena_rock["available"] is True
        assert arena_rock["duration_sec"] == 45.5
        assert arena_rock["sound_pack"] == "Arena Rock"
        assert arena_rock["url"] == "https://cdn.example.com/hero/arena_rock.mp3"
        
        # Verify head_object was called with correct key
        mock_storage_instance.head_object.assert_any_call("hero/arena_rock.mp3")
        
    def test_hero_status_object_exists_without_cdn(self, client, mock_public_storage):
        """Test hero status when object exists but no CDN domain configured."""
        # Mock storage instance
        mock_storage_instance = MagicMock()
        mock_public_storage.return_value = mock_storage_instance
        
        # Mock successful head_object response without duration metadata
        mock_storage_instance.head_object.return_value = {
            'LastModified': '2025-01-01T00:00:00Z'
        }
        
        # Set environment variables (no CDN)
        with patch.dict(os.environ, {
            'S3_PUBLIC_BUCKET': 'test-public-bucket'
        }):
            # Remove CDN domain if set
            if 'PUBLIC_CDN_DOMAIN' in os.environ:
                del os.environ['PUBLIC_CDN_DOMAIN']
            
            response = client.get("/api/hero-status")
            
        assert response.status_code == 200
        data = response.json()
        
        arena_rock = data["packs"]["Arena Rock"]
        assert arena_rock["available"] is True
        assert arena_rock["duration_sec"] == 32.0  # Default duration
        assert arena_rock["url"] == "https://test-public-bucket.s3.amazonaws.com/hero/arena_rock.mp3"
        
    def test_hero_status_object_not_found(self, client, mock_public_storage):
        """Test hero status when object doesn't exist (404)."""
        # Mock storage instance
        mock_storage_instance = MagicMock()
        mock_public_storage.return_value = mock_storage_instance
        
        # Mock head_object raising StorageError for 404
        mock_storage_instance.head_object.side_effect = StorageError("Object not found")
        
        with patch.dict(os.environ, {'S3_PUBLIC_BUCKET': 'test-public-bucket'}):
            response = client.get("/api/hero-status")
            
        assert response.status_code == 200
        data = response.json()
        
        # All packs should be unavailable
        for pack_name, pack_data in data["packs"].items():
            assert pack_data["available"] is False
            assert pack_data["duration_sec"] == 32.0
            assert pack_data["sound_pack"] == pack_name
            assert "url" not in pack_data or pack_data["url"] is None
            
    def test_hero_status_all_sound_packs_included(self, client, mock_public_storage):
        """Test that all sound packs are included in the response."""
        mock_storage_instance = MagicMock()
        mock_public_storage.return_value = mock_storage_instance
        
        # Mock head_object to always fail (objects don't exist)
        mock_storage_instance.head_object.side_effect = StorageError("Not found")
        
        response = client.get("/api/hero-status")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have all three packs
        expected_packs = ["Arena Rock", "8-Bit", "Synthwave"]
        assert set(data["packs"].keys()) == set(expected_packs)
        
    def test_hero_status_pack_slug_generation(self, client, mock_public_storage):
        """Test that sound pack names are properly converted to S3 key slugs."""
        mock_storage_instance = MagicMock()
        mock_public_storage.return_value = mock_storage_instance
        mock_storage_instance.head_object.side_effect = StorageError("Not found")
        
        response = client.get("/api/hero-status")
        
        # Verify the expected S3 keys were checked
        expected_calls = [
            "hero/arena_rock.mp3",   # "Arena Rock" -> "arena_rock"
            "hero/8_bit.mp3",        # "8-Bit" -> "8_bit" 
            "hero/synthwave.mp3"     # "Synthwave" -> "synthwave"
        ]
        
        actual_calls = [call[0][0] for call in mock_storage_instance.head_object.call_args_list]
        assert set(actual_calls) == set(expected_calls)
        
    def test_hero_status_invalid_duration_metadata(self, client, mock_public_storage):
        """Test handling of invalid duration metadata."""
        mock_storage_instance = MagicMock()
        mock_public_storage.return_value = mock_storage_instance
        
        # Mock metadata with invalid duration
        mock_storage_instance.head_object.return_value = {
            'Metadata': {'duration': 'invalid-number'},
            'LastModified': '2025-01-01T00:00:00Z'
        }
        
        with patch.dict(os.environ, {'S3_PUBLIC_BUCKET': 'test-bucket'}):
            response = client.get("/api/hero-status")
            
        assert response.status_code == 200
        data = response.json()
        
        # Should fall back to default duration
        arena_rock = data["packs"]["Arena Rock"]
        assert arena_rock["duration_sec"] == 32.0  # Default, not the invalid value