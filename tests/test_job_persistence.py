"""
Unit tests for job persistence of duration and label summary.
"""

import pytest
from src.jobstore import JobStore


class TestJobPersistence:
    """Test job metadata persistence functionality."""
    
    def test_job_finish_with_duration_and_sound_pack(self):
        """Test that finish method persists duration and sound pack."""
        job_store = JobStore()
        
        # Create and start a job
        job_id = job_store.create()
        job_store.start(job_id)
        
        # Finish with duration and sound pack
        artifacts = {
            "midi_url": "s3://bucket/path/song.mid",
            "mp3_url": "s3://bucket/path/song.mp3",
            "duration_sec": 45.5,
            "sound_pack": "Arena Rock"
        }
        
        job_store.finish(job_id, artifacts)
        
        # Retrieve job and verify metadata
        job = job_store.get(job_id)
        
        assert job.status == "done"
        assert job.midi_url == "s3://bucket/path/song.mid"
        assert job.mp3_url == "s3://bucket/path/song.mp3"
        assert job.duration_sec == 45.5
        assert job.sound_pack == "Arena Rock"
        assert job.completed_at is not None
        
    def test_job_finish_without_optional_metadata(self):
        """Test that finish works without optional duration/pack metadata."""
        job_store = JobStore()
        
        job_id = job_store.create()
        job_store.start(job_id)
        
        # Finish with minimal artifacts
        artifacts = {
            "midi_url": "s3://bucket/minimal.mid"
        }
        
        job_store.finish(job_id, artifacts)
        
        job = job_store.get(job_id)
        assert job.status == "done"
        assert job.midi_url == "s3://bucket/minimal.mid"
        assert job.duration_sec is None  # Should remain None
        assert job.sound_pack is None    # Should remain None
        
    def test_job_update_method(self):
        """Test the new update method for job metadata."""
        job_store = JobStore()
        
        job_id = job_store.create()
        
        # Update job with additional metadata
        updates = {
            "duration_sec": 32.0,
            "sound_pack": "Synthwave"
        }
        
        job_store.update(job_id, updates)
        
        # Retrieve and verify updates
        job = job_store.get(job_id)
        assert job.duration_sec == 32.0
        assert job.sound_pack == "Synthwave"
        
    def test_job_update_nonexistent_job(self):
        """Test that updating nonexistent job raises KeyError."""
        job_store = JobStore()
        
        with pytest.raises(KeyError, match="Job nonexistent not found"):
            job_store.update("nonexistent", {"duration_sec": 30.0})
            
    def test_complete_job_lifecycle_with_metadata(self):
        """Test complete job lifecycle with metadata persistence."""
        job_store = JobStore()
        
        # 1. Create job
        job_id = job_store.create()
        initial_job = job_store.get(job_id)
        assert initial_job.status == "queued"
        assert initial_job.duration_sec is None
        assert initial_job.sound_pack is None
        
        # 2. Start job
        job_store.start(job_id)
        running_job = job_store.get(job_id)
        assert running_job.status == "running"
        
        # 3. Update with additional metadata during processing
        job_store.update(job_id, {
            "sound_pack": "8-Bit", 
            "duration_sec": 28.75
        })
        
        updated_job = job_store.get(job_id)
        assert updated_job.sound_pack == "8-Bit"
        assert updated_job.duration_sec == 28.75
        assert updated_job.status == "running"  # Still running
        
        # 4. Finish with artifacts
        artifacts = {
            "midi_url": "s3://bucket/final.mid",
            "mp3_url": "s3://bucket/final.mp3",
            "momentum_json_url": "s3://bucket/final.json"
        }
        
        job_store.finish(job_id, artifacts)
        
        # 5. Verify final state
        final_job = job_store.get(job_id)
        assert final_job.status == "done"
        assert final_job.midi_url == "s3://bucket/final.mid"
        assert final_job.mp3_url == "s3://bucket/final.mp3"
        assert final_job.momentum_json_url == "s3://bucket/final.json"
        assert final_job.sound_pack == "8-Bit"          # Preserved from update
        assert final_job.duration_sec == 28.75         # Preserved from update
        assert final_job.completed_at is not None
        
    def test_job_finish_overwrites_metadata(self):
        """Test that finish method can overwrite existing metadata."""
        job_store = JobStore()
        
        job_id = job_store.create()
        job_store.start(job_id)
        
        # Set initial metadata
        job_store.update(job_id, {
            "duration_sec": 30.0,
            "sound_pack": "Arena Rock"
        })
        
        # Finish with different metadata
        artifacts = {
            "mp3_url": "s3://bucket/updated.mp3",
            "duration_sec": 45.0,     # Different duration
            "sound_pack": "Synthwave" # Different pack
        }
        
        job_store.finish(job_id, artifacts)
        
        job = job_store.get(job_id)
        assert job.duration_sec == 45.0      # Should use finish value
        assert job.sound_pack == "Synthwave" # Should use finish value
        
    def test_label_summary_persistence(self):
        """Test that label summary is persisted correctly."""
        job_store = JobStore()
        
        job_id = job_store.create()
        job_store.start(job_id)
        
        # Set label summary
        label_summary = {
            "MOMENTUM_POS": 5,
            "NEUTRAL": 3,
            "MOMENTUM_NEG": 2
        }
        
        job_store.set_label_summary(job_id, label_summary)
        
        # Finish job
        job_store.finish(job_id, {"mp3_url": "s3://test.mp3"})
        
        # Verify label summary persisted
        job = job_store.get(job_id)
        assert job.label_summary == label_summary