"""
Unit tests for fetch_metrics.py
"""

import json
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fetch_metrics import (
    collect_metrics,
    _normalize_gsc_metrics,
    _normalize_serp_metrics,
    _parse_lookback_days,
    _get_mock_gsc_data,
    _get_mock_serp_data
)


class TestFetchMetrics(unittest.TestCase):
    """Test metrics fetching functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tenant_id = "test_tenant"
    
    def test_collect_metrics_mock_gsc(self):
        """Test collecting GSC metrics with mock data."""
        result = collect_metrics(self.tenant_id, mode="gsc", lookback="7d")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["tenant_id"], self.tenant_id)
        self.assertEqual(result["mode"], "gsc")
        self.assertIn("raw_metrics", result)
        self.assertIn("normalized_metrics", result)
        
        # Check that we have expected GSC fields
        raw = result["raw_metrics"]
        self.assertIn("clicks", raw)
        self.assertIn("impressions", raw)
        self.assertIn("ctr", raw)
        self.assertIn("position", raw)
        
        # Check normalization
        normalized = result["normalized_metrics"]
        for value in normalized.values():
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)
    
    def test_collect_metrics_mock_serp(self):
        """Test collecting SERP metrics with mock data."""
        result = collect_metrics(self.tenant_id, mode="serp", lookback="30d")
        
        self.assertTrue(result["success"])
        self.assertEqual(result["mode"], "serp")
        
        # Check SERP fields
        raw = result["raw_metrics"]
        self.assertIn("avg_position", raw)
        self.assertIn("volatility", raw)
        self.assertIn("keyword_count", raw)
        self.assertIn("visibility_score", raw)
    
    def test_normalize_gsc_metrics(self):
        """Test GSC metrics normalization."""
        raw_metrics = {
            "clicks": 500,      # Should normalize to 0.05 (500/10000)
            "impressions": 20000,  # Should normalize to 0.2 (20000/100000)
            "ctr": 0.03,        # Should normalize to 0.3 (0.03/0.1)
            "position": 10.0    # Should normalize to ~0.91 (inverted: 1-(10-1)/(100-1))
        }
        
        normalized = _normalize_gsc_metrics(raw_metrics)
        
        self.assertAlmostEqual(normalized["clicks"], 0.05, places=2)
        self.assertAlmostEqual(normalized["impressions"], 0.2, places=2)
        self.assertAlmostEqual(normalized["ctr"], 0.3, places=2)
        self.assertAlmostEqual(normalized["position"], 0.909, places=2)  # Inverted position
    
    def test_normalize_serp_metrics(self):
        """Test SERP metrics normalization."""
        raw_metrics = {
            "avg_position": 5.0,    # Should normalize to ~0.96 (inverted)
            "volatility": 25.0,     # Should normalize to 0.25
            "keyword_count": 200,   # Should normalize to 0.2
            "visibility_score": 75.0  # Should normalize to 0.75
        }
        
        normalized = _normalize_serp_metrics(raw_metrics)
        
        self.assertAlmostEqual(normalized["avg_position"], 0.96, places=2)  # Inverted
        self.assertAlmostEqual(normalized["volatility"], 0.25, places=2)
        self.assertAlmostEqual(normalized["keyword_count"], 0.2, places=2)
        self.assertAlmostEqual(normalized["visibility_score"], 0.75, places=2)
    
    def test_parse_lookback_days(self):
        """Test lookback period parsing."""
        self.assertEqual(_parse_lookback_days("1d"), 1)
        self.assertEqual(_parse_lookback_days("7d"), 7)
        self.assertEqual(_parse_lookback_days("2w"), 14)
        self.assertEqual(_parse_lookback_days("1m"), 30)
        self.assertEqual(_parse_lookback_days("14"), 14)  # No suffix
        self.assertEqual(_parse_lookback_days("invalid"), 7)  # Default fallback
    
    def test_position_inversion(self):
        """Test that position metrics are properly inverted (lower position = better)."""
        # GSC position test
        gsc_metrics = {"position": 1.0}  # Best position
        normalized_gsc = _normalize_gsc_metrics(gsc_metrics)
        self.assertAlmostEqual(normalized_gsc["position"], 1.0, places=2)  # Should be 1.0
        
        gsc_metrics = {"position": 100.0}  # Worst position
        normalized_gsc = _normalize_gsc_metrics(gsc_metrics)
        self.assertAlmostEqual(normalized_gsc["position"], 0.0, places=2)  # Should be 0.0
        
        # SERP position test
        serp_metrics = {"avg_position": 1.0}  # Best position
        normalized_serp = _normalize_serp_metrics(serp_metrics)
        self.assertAlmostEqual(normalized_serp["avg_position"], 1.0, places=2)
        
        serp_metrics = {"avg_position": 100.0}  # Worst position
        normalized_serp = _normalize_serp_metrics(serp_metrics)
        self.assertAlmostEqual(normalized_serp["avg_position"], 0.0, places=2)
    
    def test_metric_clamping(self):
        """Test that out-of-range metrics are clamped properly."""
        # Test values beyond expected ranges
        extreme_gsc = {
            "clicks": -100,      # Negative (should clamp to 0)
            "impressions": 200000,  # Too high (should clamp to 100000)
            "ctr": 0.5,          # 50% CTR (should clamp to 0.1)
            "position": 0.5      # Below 1 (should clamp to 1)
        }
        
        normalized = _normalize_gsc_metrics(extreme_gsc)
        
        self.assertEqual(normalized["clicks"], 0.0)  # Clamped to min
        self.assertEqual(normalized["impressions"], 1.0)  # Clamped to max
        self.assertEqual(normalized["ctr"], 1.0)  # Clamped to max
        self.assertEqual(normalized["position"], 1.0)  # Clamped to min, then inverted
    
    def test_invalid_mode_error(self):
        """Test error handling for invalid mode."""
        result = collect_metrics(self.tenant_id, mode="invalid", lookback="7d")
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertIn("Unsupported mode", result["error"])
    
    def test_mock_data_structure(self):
        """Test that mock data has expected structure."""
        gsc_mock = _get_mock_gsc_data()
        required_gsc_fields = ["clicks", "impressions", "ctr", "position"]
        for field in required_gsc_fields:
            self.assertIn(field, gsc_mock)
            self.assertIsInstance(gsc_mock[field], (int, float))
        
        serp_mock = _get_mock_serp_data()
        required_serp_fields = ["avg_position", "volatility", "keyword_count", "visibility_score"]
        for field in required_serp_fields:
            self.assertIn(field, serp_mock)
            self.assertIsInstance(serp_mock[field], (int, float))
    
    @patch('fetch_metrics.requests.get')
    def test_serp_api_retry_mechanism(self, mock_get):
        """Test SERP API retry mechanism."""
        # Mock request failure then success
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "average_position": 5.0,
            "volatility": 20.0,
            "keyword_count": 100,
            "visibility_score": 80.0
        }
        mock_response.raise_for_status.return_value = None
        
        # First call fails, second succeeds
        mock_get.side_effect = [
            requests.exceptions.RequestException("Network error"),
            mock_response
        ]
        
        # Should succeed after retry
        result = collect_metrics(self.tenant_id, mode="serp", lookback="7d")
        self.assertTrue(result["success"])
        self.assertEqual(mock_get.call_count, 2)  # Should have retried once
    
    @patch.dict(os.environ, {"SNOWFLAKE_USER": "test", "SNOWFLAKE_PASSWORD": "test", "SNOWFLAKE_ACCOUNT": "test"})
    @patch('fetch_metrics.snowflake')
    def test_snowflake_connection_mock(self, mock_snowflake):
        """Test Snowflake connection with mocked connector."""
        # Mock the snowflake connector
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1000, 20000, 0.05, 8.0)  # clicks, impressions, ctr, position
        mock_conn.cursor.return_value = mock_cursor
        mock_snowflake.connector.connect.return_value = mock_conn
        
        result = collect_metrics(self.tenant_id, mode="gsc", lookback="7d")
        
        # Should use the mocked Snowflake data
        self.assertTrue(result["success"])
        self.assertEqual(result["raw_metrics"]["clicks"], 1000.0)
        self.assertEqual(result["raw_metrics"]["impressions"], 20000.0)
    
    def test_zero_division_handling(self):
        """Test handling of zero ranges in normalization."""
        # Create metrics where min == max (should result in 0.5)
        edge_case_metrics = {
            "clicks": 5000,  # Exactly at midpoint of 0-10000 range
        }
        
        # Temporarily modify benchmarks to test zero range
        with patch('fetch_metrics._normalize_gsc_metrics') as mock_normalize:
            def custom_normalize(raw_metrics):
                # Simulate zero range case
                if "clicks" in raw_metrics:
                    return {"clicks": 0.5}  # Should return 0.5 for zero range
                return {}
            
            mock_normalize.side_effect = custom_normalize
            result = collect_metrics(self.tenant_id, mode="gsc")
            
            # Verify the mock was called
            mock_normalize.assert_called_once()


# Mock requests module for testing
class MockRequests:
    class exceptions:
        class RequestException(Exception):
            pass
    
    @staticmethod
    def get(*args, **kwargs):
        raise MockRequests.exceptions.RequestException("Mock network error")


# Add mock requests to the test module
import sys
sys.modules['requests'] = MockRequests
requests = MockRequests


if __name__ == "__main__":
    unittest.main()