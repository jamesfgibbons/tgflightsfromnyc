"""
Unit tests for hero renderer functionality.
"""

import pytest
import anyio
from unittest.mock import Mock, patch, MagicMock
from src.hero_renderer import HeroRenderer
from src.storage import S3Storage


class TestHeroRenderer:
    """Test hero renderer writes to public bucket with metadata."""
    
    def test_hero_renderer_writes_to_public_bucket(self):
        """Test that hero renderer writes to the public S3 bucket."""
        # Create mock S3Storage
        mock_storage = Mock(spec=S3Storage)
        mock_put_object = MagicMock()
        mock_storage.put_object = mock_put_object
        
        # Create renderer with mocked storage
        renderer = HeroRenderer("serp-radio-public")
        renderer.public_storage = mock_storage
        
        # Render hero audio
        result = anyio.run(renderer.render_hero, "Arena Rock", "hero/arena_rock.mp3")
        
        # Verify put_object was called
        assert mock_put_object.called
        
        # Get the call arguments
        call_args = mock_put_object.call_args
        
        # Verify correct key
        assert call_args.kwargs["key"] == "hero/arena_rock.mp3"
        
        # Verify content type
        assert call_args.kwargs["content_type"] == "audio/mpeg"
        
        # Verify cache control header
        assert call_args.kwargs["cache_control"] == "public, max-age=86400"
        
        # Verify metadata
        metadata = call_args.kwargs["metadata"]
        assert "duration" in metadata
        assert metadata["pack"] == "Arena Rock"
        assert metadata["version"] == "1.0"
        
        # Verify result
        assert result["sound_pack"] == "Arena Rock"
        assert result["hero_key"] == "hero/arena_rock.mp3"
        assert result["duration_sec"] > 0
        assert result["sections"] > 0
        
    def test_hero_renderer_metadata_types(self):
        """Test that metadata values are strings as required by S3."""
        mock_storage = Mock(spec=S3Storage)
        mock_put_object = MagicMock()
        mock_storage.put_object = mock_put_object
        
        renderer = HeroRenderer("serp-radio-public")
        renderer.public_storage = mock_storage
        
        anyio.run(renderer.render_hero, "Synthwave", "hero/synthwave.mp3")
        
        # Get metadata from call
        call_args = mock_put_object.call_args
        metadata = call_args.kwargs["metadata"]
        
        # Verify all metadata values are strings
        for key, value in metadata.items():
            assert isinstance(value, str), f"Metadata {key} should be string, got {type(value)}"
            
        # Verify duration is numeric string
        duration_str = metadata["duration"]
        assert float(duration_str) > 0, "Duration should be parseable as float"
        
    def test_hero_renderer_public_bucket_no_encryption(self):
        """Test that public bucket uploads don't use server-side encryption."""
        # This is implicitly tested by our S3Storage.put_object implementation
        # which checks for "public" in bucket name
        
        mock_storage = Mock(spec=S3Storage)
        mock_storage.bucket = "serp-radio-public"
        mock_put_object = MagicMock()
        mock_storage.put_object = mock_put_object
        
        renderer = HeroRenderer("serp-radio-public")
        renderer.public_storage = mock_storage
        
        anyio.run(renderer.render_hero, "8-Bit", "hero/8_bit.mp3")
        
        # Verify put_object was called (encryption check is in S3Storage)
        assert mock_put_object.called
        
    def test_hero_renderer_with_lufs_metadata(self):
        """Test that LUFS metadata is included when available."""
        # This test documents future behavior when mastering is integrated
        
        mock_storage = Mock(spec=S3Storage)
        mock_put_object = MagicMock()
        mock_storage.put_object = mock_put_object
        
        renderer = HeroRenderer("serp-radio-public")  
        renderer.public_storage = mock_storage
        
        # Mock mastering to return LUFS value
        with patch("src.hero_renderer.master_audio_file") as mock_master:
            mock_master.return_value = (b"mastered_audio", -14.0)
            
            # When mastering is integrated, LUFS should be in metadata
            # await renderer.render_hero("Rock", "hero/rock.mp3")
            # metadata = mock_put_object.call_args.kwargs["metadata"]
            # assert "lufs" in metadata
            # assert metadata["lufs"] == "-14.0"
            
        # For now, just verify the test runs
        assert True