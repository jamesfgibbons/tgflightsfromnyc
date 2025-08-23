"""
Unit tests for job store operations.
"""

import pytest
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from src.jobstore import JobStore
from src.models import JobStatus


@pytest.fixture
def job_store():
    """Create fresh job store for each test."""
    store = JobStore()
    yield store
    store.clear()


class TestJobStore:
    """Test job store operations."""
    
    def test_create_job(self, job_store):
        """Test creating new job."""
        job_id = job_store.create()
        
        assert job_id is not None
        assert len(job_id) > 0
        
        job = job_store.get(job_id)
        assert job.job_id == job_id
        assert job.status == "queued"
        assert job.created_at is not None
    
    def test_create_job_with_id(self, job_store):
        """Test creating job with specific ID."""
        job_id = "test-job-123"
        result_id = job_store.create(job_id)
        
        assert result_id == job_id
        
        job = job_store.get(job_id)
        assert job.job_id == job_id
    
    def test_create_duplicate_job(self, job_store):
        """Test creating job with duplicate ID fails."""
        job_id = "duplicate-job"
        job_store.create(job_id)
        
        with pytest.raises(ValueError, match="already exists"):
            job_store.create(job_id)
    
    def test_start_job(self, job_store):
        """Test starting queued job."""
        job_id = job_store.create()
        job_store.start(job_id)
        
        job = job_store.get(job_id)
        assert job.status == "running"
    
    def test_start_nonexistent_job(self, job_store):
        """Test starting non-existent job fails."""
        with pytest.raises(KeyError, match="not found"):
            job_store.start("nonexistent")
    
    def test_start_job_wrong_state(self, job_store):
        """Test starting job in wrong state fails."""
        job_id = job_store.create()
        job_store.start(job_id)
        
        with pytest.raises(ValueError, match="not in queued state"):
            job_store.start(job_id)  # Already running
    
    def test_finish_job(self, job_store):
        """Test finishing running job."""
        job_id = job_store.create()
        job_store.start(job_id)
        
        artifacts = {
            "midi_url": "s3://bucket/file.mid",
            "mp3_url": "s3://bucket/file.mp3"
        }
        job_store.finish(job_id, artifacts)
        
        job = job_store.get(job_id)
        assert job.status == "done"
        assert job.midi_url == artifacts["midi_url"]
        assert job.mp3_url == artifacts["mp3_url"]
        assert job.completed_at is not None
    
    def test_fail_job(self, job_store):
        """Test failing job with error."""
        job_id = job_store.create()
        job_store.start(job_id)
        
        error_msg = "Something went wrong"
        job_store.fail(job_id, error_msg)
        
        job = job_store.get(job_id)
        assert job.status == "error"
        assert job.error == error_msg
        assert job.completed_at is not None
    
    def test_set_label_summary(self, job_store):
        """Test setting label summary."""
        job_id = job_store.create()
        
        summary = {"MOMENTUM_POS": 2, "NEUTRAL": 1}
        job_store.set_label_summary(job_id, summary)
        
        job = job_store.get(job_id)
        assert job.label_summary == summary
    
    def test_get_nonexistent_job(self, job_store):
        """Test getting non-existent job fails."""
        with pytest.raises(KeyError, match="not found"):
            job_store.get("nonexistent")
    
    def test_list_jobs(self, job_store):
        """Test listing jobs."""
        job1 = job_store.create("job1")
        job2 = job_store.create("job2")
        job_store.start(job1)
        
        all_jobs = job_store.list_jobs()
        assert len(all_jobs) == 2
        assert job1 in all_jobs
        assert job2 in all_jobs
        
        # Test status filter
        running_jobs = job_store.list_jobs(status="running")
        assert len(running_jobs) == 1
        assert job1 in running_jobs
        
        queued_jobs = job_store.list_jobs(status="queued")
        assert len(queued_jobs) == 1
        assert job2 in queued_jobs
    
    def test_job_isolation(self, job_store):
        """Test that job data is properly isolated."""
        job_id = job_store.create()
        
        # Get job and modify returned object
        job = job_store.get(job_id)
        job.status = "hacked"
        
        # Original should be unchanged
        original_job = job_store.get(job_id)
        assert original_job.status == "queued"


class TestJobStoreConcurrency:
    """Test job store thread safety."""
    
    def test_concurrent_job_creation(self, job_store):
        """Test concurrent job creation."""
        def create_job(i):
            return job_store.create(f"job-{i}")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_job, i) for i in range(50)]
            job_ids = [f.result() for f in futures]
        
        # All jobs should be created successfully
        assert len(job_ids) == 50
        assert len(set(job_ids)) == 50  # All unique
        assert job_store.size() == 50
    
    def test_concurrent_job_operations(self, job_store):
        """Test concurrent operations on same job."""
        job_id = job_store.create("concurrent-test")
        
        def start_job():
            try:
                job_store.start(job_id)
                return "started"
            except ValueError:
                return "already_running"
        
        # Try to start same job concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(start_job) for _ in range(5)]
            results = [f.result() for f in futures]
        
        # Only one should succeed, others should fail
        assert results.count("started") == 1
        assert results.count("already_running") == 4
        
        job = job_store.get(job_id)
        assert job.status == "running"
    
    def test_concurrent_read_write(self, job_store):
        """Test concurrent read/write operations."""
        job_id = job_store.create("read-write-test")
        
        def update_job():
            job_store.set_label_summary(job_id, {"TEST": 1})
        
        def read_job():
            return job_store.get(job_id)
        
        # Mix read and write operations
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for i in range(20):
                if i % 2 == 0:
                    futures.append(executor.submit(update_job))
                else:
                    futures.append(executor.submit(read_job))
            
            # Wait for all operations
            for f in futures:
                f.result()
        
        # Final state should be consistent
        job = job_store.get(job_id)
        assert job.label_summary == {"TEST": 1}