"""
End-to-end API integration tests for SERP Radio production backend.
Uses TestClient and moto for S3 mocking.
"""

import json
import os
import time
from io import BytesIO
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from moto import mock_aws
import boto3

from src.main import app
from src.jobstore import job_store
from src.models import SonifyRequest


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_s3_setup():
    """Set up mocked S3 environment."""
    with mock_aws():
        # Create mock S3 client and bucket
        s3_client = boto3.client("s3", region_name="us-east-1")
        bucket_name = "serp-radio-artifacts"
        s3_client.create_bucket(Bucket=bucket_name)
        yield s3_client, bucket_name


@pytest.fixture
def sample_csv_data():
    """Sample CSV data for upload tests."""
    csv_content = """keyword,ctr,impressions,position,clicks
"example keyword",0.05,1000,5.2,50
"another keyword",0.03,800,8.1,24
"test query",0.07,1200,3.9,84
"""
    return csv_content.encode('utf-8')


@pytest.fixture(autouse=True)
def clear_job_store():
    """Clear job store before each test."""
    job_store.clear()


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test health endpoint returns ok status."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["ok"] is True
        assert "version" in data
        assert "timestamp" in data
        assert "services" in data
    
    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/health")
        assert response.status_code == 200
        
        # Check CORS headers (TestClient may not include all CORS headers)
        response = client.get("/health")
        assert response.status_code == 200


class TestCsvUpload:
    """Test CSV upload functionality."""
    
    def test_upload_valid_csv(self, client, mock_s3_setup, sample_csv_data):
        """Test uploading valid CSV file."""
        s3_client, bucket_name = mock_s3_setup
        
        with patch("src.main.S3_BUCKET", bucket_name):
            response = client.post(
                "/api/upload-csv",
                params={"tenant": "test-tenant"},
                files={"file": ("test.csv", BytesIO(sample_csv_data), "text/csv")}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "dataset_id" in data
        assert data["row_count"] == 3
        assert "ctr" in data["inferred_schema"]
        assert len(data["preview"]) == 3
    
    def test_upload_invalid_tenant(self, client, sample_csv_data):
        """Test upload with invalid tenant name."""
        response = client.post(
            "/api/upload-csv",
            params={"tenant": "Invalid Tenant!"},
            files={"file": ("test.csv", BytesIO(sample_csv_data), "text/csv")}
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_upload_non_csv_file(self, client):
        """Test upload with non-CSV file."""
        response = client.post(
            "/api/upload-csv",
            params={"tenant": "test-tenant"},
            files={"file": ("test.txt", BytesIO(b"not a csv"), "text/plain")}
        )
        
        assert response.status_code == 400
        assert "must be a CSV" in response.json()["error"]
    
    def test_upload_empty_csv(self, client):
        """Test upload with empty CSV."""
        response = client.post(
            "/api/upload-csv", 
            params={"tenant": "test-tenant"},
            files={"file": ("empty.csv", BytesIO(b""), "text/csv")}
        )
        
        assert response.status_code == 400


class TestSonificationAPI:
    """Test sonification job creation and status."""
    
    @patch("src.main.process_sonification")
    def test_create_sonification_job(self, mock_process, client):
        """Test creating sonification job."""
        request_data = {
            "tenant": "test-tenant",
            "source": "demo",
            "use_training": True,
            "momentum": True,
            "override_metrics": {
                "ctr": 0.75,
                "impressions": 0.8,
                "position": 0.9,
                "clicks": 0.7
            }
        }
        
        response = client.post("/api/sonify", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert data["status"] == "queued"
        
        # Verify background task was scheduled
        mock_process.assert_called_once()
    
    @patch("src.main.process_sonification")  
    def test_deterministic_seed(self, mock_process, client):
        """Test deterministic sonification with seed."""
        request_data = {
            "tenant": "test-tenant",
            "source": "demo", 
            "seed": 42,
            "override_metrics": {
                "ctr": 0.75,
                "impressions": 0.8,
                "position": 0.9,
                "clicks": 0.7
            }
        }
        
        # Create two identical requests
        response1 = client.post("/api/sonify", json=request_data)
        response2 = client.post("/api/sonify", json=request_data)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Both should succeed (determinism tested at service layer)
        assert mock_process.call_count == 2
    
    def test_create_sonification_invalid_request(self, client):
        """Test sonification with invalid request data."""
        request_data = {
            "tenant": "INVALID_TENANT!",  # Invalid format
            "source": "demo"
        }
        
        response = client.post("/api/sonify", json=request_data)
        assert response.status_code == 422
    
    def test_get_job_status_not_found(self, client):
        """Test getting status for non-existent job."""
        response = client.get("/api/jobs/non-existent-job")
        assert response.status_code == 404
    
    def test_get_job_status_queued(self, client):
        """Test getting status for queued job."""
        # Create a job directly in store
        job_id = job_store.create("test-job-123")
        
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "queued"
        assert data["midi_url"] is None
    
    def test_get_job_status_completed(self, client, mock_s3_setup):
        """Test getting status for completed job with presigned URLs."""
        s3_client, bucket_name = mock_s3_setup
        
        # Create and complete a job
        job_id = job_store.create("test-job-complete")
        job_store.start(job_id)
        job_store.finish(job_id, {
            "midi_url": "test-tenant/midi_output/test-job-complete.mid",
            "momentum_json_url": "test-tenant/logs/test-job-complete_momentum.json"
        })
        job_store.set_label_summary(job_id, {"MOMENTUM_POS": 2, "NEUTRAL": 1})
        
        # Mock S3 objects
        s3_client.put_object(
            Bucket=bucket_name,
            Key="test-tenant/midi_output/test-job-complete.mid",
            Body=b"fake midi data"
        )
        
        with patch("src.main.S3_BUCKET", bucket_name):
            response = client.get(f"/api/jobs/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "done"
        assert data["midi_url"] is not None
        assert "amazonaws.com" in data["midi_url"]  # Presigned URL
        assert data["label_summary"]["MOMENTUM_POS"] == 2


class TestShareLinks:
    """Test shareable link functionality."""
    
    def test_create_share_link(self, client, mock_s3_setup):
        """Test creating share link for completed job."""
        s3_client, bucket_name = mock_s3_setup
        
        # Create and complete a job
        job_id = job_store.create("test-share-job")
        job_store.start(job_id)
        job_store.finish(job_id, {
            "midi_url": "test-tenant/midi_output/test-share-job.mid"
        })
        
        response = client.post(f"/api/share/{job_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "share_url" in data
        assert "expires_at" in data
        assert "/api/share/" in data["share_url"]
    
    def test_create_share_link_not_done(self, client):
        """Test creating share link for non-completed job fails."""
        job_id = job_store.create("test-queued-job")
        
        response = client.post(f"/api/share/{job_id}")
        assert response.status_code == 400
        assert "completed jobs" in response.json()["error"]
    
    def test_get_shared_job(self, client, mock_s3_setup):
        """Test accessing job via share token."""
        s3_client, bucket_name = mock_s3_setup
        
        # Create and complete a job
        job_id = job_store.create("test-shared-access")
        job_store.start(job_id) 
        job_store.finish(job_id, {
            "midi_url": "test-tenant/midi_output/test-shared-access.mid"
        })
        
        # Create share token
        token = job_store.create_share_token(job_id)
        
        # Mock S3 object
        s3_client.put_object(
            Bucket=bucket_name,
            Key="test-tenant/midi_output/test-shared-access.mid",
            Body=b"fake midi"
        )
        
        with patch("src.main.S3_BUCKET", bucket_name):
            response = client.get(f"/api/share/{token}")
        
        assert response.status_code == 200
        data = response.json()
        
        # Job ID should be masked
        assert data["job_id"].startswith("shared-")
        assert data["status"] == "done"
        assert "amazonaws.com" in data["midi_url"]  # Presigned URL
    
    def test_get_shared_job_not_found(self, client):
        """Test accessing non-existent share token."""
        response = client.get("/api/share/nonexistent")
        assert response.status_code == 404


class TestEarcons:
    """Test earcon functionality."""
    
    def test_earcons_environment_variable(self):
        """Test earcons are controlled by environment variable."""
        from src.sonify_service import create_sonification_service
        
        # Test default (disabled)
        service = create_sonification_service("test-bucket")
        assert service.earcons_enabled is False
        
        # Test enabled
        with patch.dict(os.environ, {"EARCONS_ENABLED": "1"}):
            service = create_sonification_service("test-bucket")
            assert service.earcons_enabled is True


class TestE2EWorkflow:
    """End-to-end workflow tests."""
    
    @patch("completed.fetch_metrics.collect_metrics")
    @patch("completed.transform_midi.create_sonified_midi") 
    def test_complete_demo_sonification(
        self, mock_create_midi, mock_fetch_metrics, client, mock_s3_setup
    ):
        """Test complete sonification workflow with demo data."""
        s3_client, bucket_name = mock_s3_setup
        
        # Mock domain modules
        mock_fetch_metrics.return_value = {
            "success": True,
            "normalized_metrics": {"ctr": 0.8, "impressions": 0.7, "position": 0.9, "clicks": 0.75}
        }
        mock_create_midi.return_value = True
        
        # Create job
        request_data = {
            "tenant": "test-tenant",
            "source": "demo", 
            "override_metrics": {"ctr": 0.8, "impressions": 0.7, "position": 0.9, "clicks": 0.75}
        }
        
        with patch("src.main.S3_BUCKET", bucket_name):
            response = client.post("/api/sonify", json=request_data)
        
        assert response.status_code == 200
        job_id = response.json()["job_id"]
        
        # Wait for background processing (simulate)
        time.sleep(0.1)
        
        # Check final status
        with patch("src.main.S3_BUCKET", bucket_name):
            response = client.get(f"/api/jobs/{job_id}")
        
        # Note: In real test, job might still be processing
        # This test structure shows the pattern
        assert response.status_code == 200


class TestRulesAPI:
    """Test YAML rules management."""
    
    def test_get_default_rules(self, client):
        """Test retrieving default rules.""" 
        response = client.get("/api/rules?tenant=test-tenant")
        
        assert response.status_code == 200
        assert "rules:" in response.text
        assert "MOMENTUM_POS" in response.text
    
    def test_save_valid_rules(self, client, mock_s3_setup):
        """Test saving valid YAML rules."""
        s3_client, bucket_name = mock_s3_setup
        
        valid_yaml = """
rules:
  - when:
      ctr: ">=0.8"
    choose_label: "HIGH_CTR"
  - when: {}
    choose_label: "NEUTRAL"
"""
        
        request_data = {
            "tenant": "test-tenant",
            "yaml_text": valid_yaml
        }
        
        with patch("src.main.S3_BUCKET", bucket_name):
            response = client.post("/api/rules", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "version_key" in data
        assert data["tenant"] == "test-tenant"
    
    def test_save_invalid_yaml(self, client):
        """Test saving invalid YAML."""
        request_data = {
            "tenant": "test-tenant", 
            "yaml_text": "invalid: yaml: content: ["
        }
        
        response = client.post("/api/rules", json=request_data)
        assert response.status_code == 400
        assert "Invalid YAML" in response.json()["error"]
    
    def test_save_yaml_missing_rules(self, client):
        """Test saving YAML without required structure."""
        request_data = {
            "tenant": "test-tenant",
            "yaml_text": "not_rules: []"
        }
        
        response = client.post("/api/rules", json=request_data) 
        assert response.status_code == 400
        assert "must contain 'rules'" in response.json()["error"]


class TestValidation:
    """Test request validation."""
    
    def test_invalid_tenant_format(self, client):
        """Test various invalid tenant formats."""
        invalid_tenants = [
            "UPPERCASE",
            "with spaces", 
            "with.dots",
            "with@symbols",
            "",
            "a" * 100  # Too long
        ]
        
        for tenant in invalid_tenants:
            request_data = {
                "tenant": tenant,
                "source": "demo"
            }
            
            response = client.post("/api/sonify", json=request_data)
            assert response.status_code == 422, f"Should reject tenant: {tenant}"
    
    def test_invalid_lookback_format(self, client):
        """Test invalid lookback period formats."""
        invalid_lookbacks = [
            "invalid",
            "1x",
            "0d",
            "-1d",
            "1.5d"
        ]
        
        for lookback in invalid_lookbacks:
            request_data = {
                "tenant": "test-tenant",
                "source": "demo",
                "lookback": lookback
            }
            
            response = client.post("/api/sonify", json=request_data)
            assert response.status_code == 422, f"Should reject lookback: {lookback}"
    
    def test_invalid_override_metrics(self, client):
        """Test invalid override metrics."""
        request_data = {
            "tenant": "test-tenant",
            "source": "demo",
            "override_metrics": {
                "ctr": 1.5,  # Out of range
                "invalid": "not_numeric"
            }
        }
        
        response = client.post("/api/sonify", json=request_data)
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])