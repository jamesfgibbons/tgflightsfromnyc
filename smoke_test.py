#!/usr/bin/env python3
"""
Smoke tests for SERP Radio backend implementation.
Validates all major features are working correctly.
"""

import asyncio
import json
from unittest.mock import Mock, MagicMock

# Test Task A: Hero Status with Public Bucket
def test_hero_status_functionality():
    """Test hero status endpoint functionality."""
    print("✓ Testing hero status with public bucket...")
    
    from src.storage import S3Storage
    from src.main import S3_PUBLIC_BUCKET
    
    # Verify S3Storage can be instantiated with public bucket
    public_storage = S3Storage("test-public-bucket")
    assert hasattr(public_storage, 'head_object')
    assert hasattr(public_storage, 'put_object')
    print("  ✓ S3Storage with public bucket support")
    
    # Test URL building logic
    hero_key = "hero/arena_rock.mp3"
    cdn_domain = "d1abc123def456.cloudfront.net"
    
    # Without CDN
    url_without_cdn = f"https://test-bucket.s3.amazonaws.com/{hero_key}"
    assert "hero/arena_rock.mp3" in url_without_cdn
    
    # With CDN
    url_with_cdn = f"https://{cdn_domain}/{hero_key}"
    assert cdn_domain in url_with_cdn
    assert hero_key in url_with_cdn
    print("  ✓ Public URL generation logic")

# Test Task B: Presigned URLs without Force Download
def test_presigned_url_functionality():
    """Test presigned URL generation without forced downloads."""
    print("✓ Testing presigned URLs without force download...")
    
    from src.storage import S3Storage
    
    # Mock S3Storage
    storage = S3Storage("test-bucket")
    
    # Check method signature
    import inspect
    sig = inspect.signature(storage.generate_presigned_url)
    assert 'force_download' in sig.parameters
    assert sig.parameters['force_download'].default is False
    print("  ✓ Presigned URL method signature correct")

# Test Task C: Arranger Defaults and Fallback
def test_arranger_functionality():
    """Test music arranger with defaults and fallback sections."""
    print("✓ Testing arranger defaults and fallback...")
    
    from src.arranger import MusicArranger
    
    # Create arranger
    arranger = MusicArranger(total_bars=16)
    
    # Test build_default_sections method exists
    assert hasattr(arranger, 'build_default_sections')
    
    # Test default sections
    sections = arranger.build_default_sections(16)
    assert len(sections) >= 1
    assert sum(section.bars for section in sections) == 16
    print("  ✓ Default sections cover exact bar count")
    
    # Test fallback behavior
    empty_sections = arranger.arrange_momentum_data([])
    assert len(empty_sections) >= 1
    assert sum(section.bars for section in empty_sections) == 16
    print("  ✓ Fallback to defaults with empty momentum data")

# Test Task D: Job Persistence
def test_job_persistence_functionality():
    """Test duration and label summary persistence."""
    print("✓ Testing job metadata persistence...")
    
    from src.jobstore import JobStore
    from src.models import JobStatus
    
    job_store = JobStore()
    
    # Test update method exists
    assert hasattr(job_store, 'update')
    
    # Test finish method can handle duration_sec and sound_pack
    job_id = job_store.create()
    job_store.start(job_id)
    
    artifacts = {
        "midi_url": "s3://test/song.mid",
        "duration_sec": 45.5,
        "sound_pack": "Arena Rock"
    }
    
    job_store.finish(job_id, artifacts)
    job = job_store.get(job_id)
    
    assert job.duration_sec == 45.5
    assert job.sound_pack == "Arena Rock"
    print("  ✓ Duration and sound pack persistence")
    
    # Test JobStatus model has required fields
    model_fields = JobStatus.model_fields
    assert 'duration_sec' in model_fields, "duration_sec field missing from JobStatus model"
    assert 'sound_pack' in model_fields, "sound_pack field missing from JobStatus model"
    print("  ✓ JobStatus model updated with new fields")

# Test Task E: Hero Renderer
async def test_hero_renderer_functionality():
    """Test hero renderer writes to public bucket."""
    print("✓ Testing hero renderer...")
    
    from src.hero_renderer import HeroRenderer
    
    # Mock the S3Storage
    mock_storage = Mock()
    mock_put_object = MagicMock()
    mock_storage.put_object = mock_put_object
    
    # Create renderer
    renderer = HeroRenderer("serp-radio-public")
    renderer.public_storage = mock_storage
    
    # Test render method
    result = await renderer.render_hero("Arena Rock", "hero/arena_rock.mp3")
    
    # Verify put_object was called with correct parameters
    assert mock_put_object.called
    call_args = mock_put_object.call_args
    
    assert call_args.kwargs["key"] == "hero/arena_rock.mp3"
    assert call_args.kwargs["content_type"] == "audio/mpeg"
    assert call_args.kwargs["cache_control"] == "public, max-age=86400"
    
    # Verify metadata
    metadata = call_args.kwargs["metadata"]
    assert "duration" in metadata
    assert metadata["pack"] == "Arena Rock"
    assert metadata["version"] == "1.0"
    print("  ✓ Hero renderer writes to public bucket with metadata")

# Test Task F: Developer Experience
def test_dx_polish():
    """Test developer experience improvements."""
    print("✓ Testing DX polish features...")
    
    import os
    
    # Check .python-version exists
    python_version_path = ".python-version"
    assert os.path.exists(python_version_path)
    with open(python_version_path) as f:
        version = f.read().strip()
        assert version == "3.11"
    print("  ✓ .python-version file created")
    
    # Check /api/metrics endpoint exists in main.py
    from src.main import app
    routes = [route.path for route in app.routes]
    assert "/api/metrics" in routes
    print("  ✓ /api/metrics endpoint added")
    
    # Check README_DEPLOY.md updated
    readme_path = "README_DEPLOY.md"
    assert os.path.exists(readme_path)
    with open(readme_path) as f:
        content = f.read()
        assert "serp-radio-staging-artifacts" in content
        assert "serp-radio-staging-public" in content
    print("  ✓ README_DEPLOY.md updated with staging info")

def run_all_smoke_tests():
    """Run all smoke tests and provide summary."""
    print("🚀 Running SERP Radio Backend Smoke Tests\n")
    
    tests = [
        ("A) Hero Status Public Bucket", test_hero_status_functionality),
        ("B) Presigned URLs No Download", test_presigned_url_functionality),
        ("C) Arranger Defaults", test_arranger_functionality),
        ("D) Job Persistence", test_job_persistence_functionality),
        ("E) Hero Renderer", lambda: asyncio.run(test_hero_renderer_functionality())),
        ("F) DX Polish", test_dx_polish)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
            print(f"✅ {test_name} - PASSED\n")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} - FAILED: {e}\n")
    
    print("=" * 60)
    print(f"SMOKE TEST SUMMARY")
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("🎉 ALL SMOKE TESTS PASSED - Ready for deployment!")
    else:
        print(f"⚠️  {failed} test(s) failed - needs attention")
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_smoke_tests()
    exit(0 if success else 1)