"""
In-memory job store for SERP Radio production backend.
TODO: Replace with DynamoDB for production scaling.
"""

import threading
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional
import secrets
import string

from .models import JobStatus


class JobStore:
    """
    Thread-safe in-memory job store for PoC.
    
    TODO: Replace with DynamoDB implementation for production:
    - Table: serp-radio-jobs
    - Partition key: job_id
    - TTL: 7 days for completed jobs
    - GSI: tenant-index for tenant-specific queries
    """
    
    def __init__(self):
        self._jobs: Dict[str, JobStatus] = {}
        self._shares: Dict[str, Dict[str, str]] = {}  # token -> {job_id, expires_at}
        self._lock = threading.Lock()
    
    def create(self, job_id: Optional[str] = None) -> str:
        """
        Create new job record.
        
        Args:
            job_id: Optional job ID, generates UUID if None
        
        Returns:
            Job ID string
        """
        if job_id is None:
            job_id = str(uuid.uuid4())
        
        with self._lock:
            if job_id in self._jobs:
                raise ValueError(f"Job {job_id} already exists")
            
            self._jobs[job_id] = JobStatus(
                job_id=job_id,
                status="queued",
                created_at=datetime.utcnow().isoformat()
            )
        
        return job_id
    
    def start(self, job_id: str) -> None:
        """
        Mark job as running.
        
        Args:
            job_id: Job identifier
        
        Raises:
            KeyError: If job not found
            ValueError: If job not in queued state
        """
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(f"Job {job_id} not found")
            
            job = self._jobs[job_id]
            if job.status != "queued":
                raise ValueError(f"Job {job_id} not in queued state (current: {job.status})")
            
            # Update status
            job.status = "running"
    
    def update(self, job_id: str, updates: Dict[str, any]) -> None:
        """
        Update job with additional metadata.
        
        Args:
            job_id: Job identifier
            updates: Dictionary of fields to update
        
        Raises:
            KeyError: If job not found
        """
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(f"Job {job_id} not found")
            
            job = self._jobs[job_id]
            
            # Update job fields dynamically
            for key, value in updates.items():
                setattr(job, key, value)

    def finish(self, job_id: str, artifacts: Dict[str, str]) -> None:
        """
        Mark job as completed with artifacts.
        
        Args:
            job_id: Job identifier
            artifacts: Dictionary of artifact URLs and metadata
        
        Raises:
            KeyError: If job not found
            ValueError: If job not in running state
        """
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(f"Job {job_id} not found")
            
            job = self._jobs[job_id]
            if job.status != "running":
                raise ValueError(f"Job {job_id} not in running state (current: {job.status})")
            
            # Update job with artifacts and metadata
            job.status = "done"
            job.completed_at = datetime.utcnow().isoformat()
            job.midi_url = artifacts.get("midi_url")
            job.mp3_url = artifacts.get("mp3_url") 
            job.momentum_json_url = artifacts.get("momentum_json_url")
            job.log_url = artifacts.get("log_url")
            
            # Add new metadata fields
            if "duration_sec" in artifacts:
                job.duration_sec = artifacts["duration_sec"]
            if "sound_pack" in artifacts:
                job.sound_pack = artifacts["sound_pack"]
    
    def fail(self, job_id: str, error: str) -> None:
        """
        Mark job as failed with error message.
        
        Args:
            job_id: Job identifier
            error: Error message
        
        Raises:
            KeyError: If job not found
        """
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(f"Job {job_id} not found")
            
            job = self._jobs[job_id]
            job.status = "error"
            job.error = error
            job.completed_at = datetime.utcnow().isoformat()
    
    def get(self, job_id: str) -> JobStatus:
        """
        Get job status.
        
        Args:
            job_id: Job identifier
        
        Returns:
            JobStatus instance
        
        Raises:
            KeyError: If job not found
        """
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(f"Job {job_id} not found")
            
            # Return a copy to avoid external mutation
            return JobStatus.model_validate(self._jobs[job_id].model_dump())
    
    def set_label_summary(self, job_id: str, label_summary: Dict[str, int]) -> None:
        """
        Update job with label summary.
        
        Args:
            job_id: Job identifier
            label_summary: Dictionary of label counts
        
        Raises:
            KeyError: If job not found
        """
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(f"Job {job_id} not found")
            
            self._jobs[job_id].label_summary = label_summary
    
    def list_jobs(self, tenant: Optional[str] = None, status: Optional[str] = None) -> Dict[str, JobStatus]:
        """
        List jobs with optional filtering.
        
        Args:
            tenant: Filter by tenant (not implemented in PoC)
            status: Filter by status
        
        Returns:
            Dictionary of job_id -> JobStatus
        """
        with self._lock:
            jobs = {}
            for job_id, job in self._jobs.items():
                # Status filter
                if status and job.status != status:
                    continue
                
                # TODO: Tenant filtering when tenant is stored in job
                jobs[job_id] = JobStatus.model_validate(job.model_dump())
            
            return jobs
    
    def create_share_token(self, job_id: str, ttl_hours: int = 24) -> str:
        """
        Create shareable token for job.
        
        Args:
            job_id: Job identifier
            ttl_hours: Token time-to-live in hours
        
        Returns:
            Share token string
        
        Raises:
            KeyError: If job not found
        """
        with self._lock:
            if job_id not in self._jobs:
                raise KeyError(f"Job {job_id} not found")
            
            # Generate URL-safe token
            token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
            
            self._shares[token] = {
                "job_id": job_id,
                "expires_at": expires_at.isoformat()
            }
            
            return token
    
    def get_job_by_share_token(self, token: str) -> JobStatus:
        """
        Get job by share token.
        
        Args:
            token: Share token
        
        Returns:
            JobStatus instance with masked job_id
        
        Raises:
            KeyError: If token not found or expired
        """
        with self._lock:
            if token not in self._shares:
                raise KeyError(f"Share token not found")
            
            share_info = self._shares[token]
            expires_at = datetime.fromisoformat(share_info["expires_at"])
            
            if datetime.utcnow() > expires_at:
                # Clean up expired token
                del self._shares[token]
                raise KeyError(f"Share token expired")
            
            job_id = share_info["job_id"]
            if job_id not in self._jobs:
                raise KeyError(f"Job {job_id} not found")
            
            # Return copy with masked job_id
            job = JobStatus.model_validate(self._jobs[job_id].model_dump())
            job.job_id = f"shared-{token[:8]}"  # Mask actual job_id
            return job
    
    def clear(self) -> None:
        """Clear all jobs and shares (for testing)."""
        with self._lock:
            self._jobs.clear()
            self._shares.clear()
    
    def size(self) -> int:
        """Get number of jobs in store."""
        with self._lock:
            return len(self._jobs)


# Global instance for PoC
# TODO: Replace with dependency injection when moving to DynamoDB
job_store = JobStore()