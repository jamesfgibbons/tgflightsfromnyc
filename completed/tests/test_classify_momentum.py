"""
Unit tests for classify_momentum.py
"""

import json
import unittest
import sys
import os
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from classify_momentum import (
    classify_momentum_from_tokens, 
    _classify_section_momentum,
    _calculate_pitch_slope,
    analyze_momentum_distribution
)


class TestClassifyMomentum(unittest.TestCase):
    """Test momentum classification functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tenant_id = "test_tenant"
        self.file_id = "test_file"
    
    def _create_token_data(self, sections_data: List[Dict]) -> Dict[str, Any]:
        """Create token data structure for testing."""
        tokens = []
        for i, section_data in enumerate(sections_data):
            token = {
                "section_id": f"{self.file_id}_section_{i}",
                "hash": f"hash_{i}",
                "bars_covered": section_data.get("bars_covered", 4),
                "start_bar": i * 4,
                "end_bar": (i * 4) + 3,
                "token_sequence": section_data.get("token_sequence", []),
                "metadata": section_data.get("metadata", {
                    "note_count": 8,
                    "avg_pitch": 60.0,
                    "avg_velocity": 64.0,
                    "avg_bpm": 120.0,
                    "pitch_range": 12,
                    "duration": 8.0
                })
            }
            tokens.append(token)
        
        return {
            "error": False,
            "tenant_id": self.tenant_id,
            "file_id": self.file_id,
            "total_sections": len(tokens),
            "unique_sections": len(tokens),
            "tokens": tokens
        }
    
    def test_positive_momentum_classification(self):
        """Test classification of positive momentum section."""
        # High tempo, high velocity, rising pitch
        positive_section = {
            "metadata": {
                "avg_bpm": 150.0,  # Fast tempo
                "avg_velocity": 100.0,  # Loud
                "note_count": 16
            },
            "token_sequence": [
                ["NOTE_ON", 60, 100, 0.0],
                ["NOTE_OFF", 60, 0, 1.0],
                ["NOTE_ON", 65, 100, 2.0],  # Rising pitch
                ["NOTE_OFF", 65, 0, 3.0],
                ["NOTE_ON", 70, 100, 4.0],  # Higher pitch
                ["NOTE_OFF", 70, 0, 5.0]
            ]
        }
        
        token_data = self._create_token_data([positive_section])
        result = classify_momentum_from_tokens(token_data)
        
        self.assertFalse(result.get("error", True))
        self.assertEqual(len(result["momentum"]), 1)
        
        momentum = result["momentum"][0]
        self.assertEqual(momentum["label"], "positive")
        self.assertGreater(momentum["score"], 0.65)
    
    def test_negative_momentum_classification(self):
        """Test classification of negative momentum section."""
        # Low tempo, low velocity, falling pitch
        negative_section = {
            "metadata": {
                "avg_bpm": 70.0,  # Slow tempo
                "avg_velocity": 30.0,  # Quiet
                "note_count": 4
            },
            "token_sequence": [
                ["NOTE_ON", 72, 30, 0.0],  # High pitch
                ["NOTE_OFF", 72, 0, 2.0],
                ["NOTE_ON", 67, 30, 4.0],  # Lower pitch
                ["NOTE_OFF", 67, 0, 6.0],
                ["NOTE_ON", 60, 30, 8.0],  # Even lower
                ["NOTE_OFF", 60, 0, 10.0]
            ]
        }
        
        token_data = self._create_token_data([negative_section])
        result = classify_momentum_from_tokens(token_data)
        
        self.assertFalse(result.get("error", True))
        momentum = result["momentum"][0]
        self.assertEqual(momentum["label"], "negative")
        self.assertLess(momentum["score"], 0.35)
    
    def test_neutral_momentum_classification(self):
        """Test classification of neutral momentum section."""
        # Medium tempo, medium velocity, stable pitch
        neutral_section = {
            "metadata": {
                "avg_bpm": 110.0,  # Medium tempo
                "avg_velocity": 65.0,  # Medium volume
                "note_count": 8
            },
            "token_sequence": [
                ["NOTE_ON", 64, 65, 0.0],
                ["NOTE_OFF", 64, 0, 1.0],
                ["NOTE_ON", 64, 65, 2.0],  # Same pitch
                ["NOTE_OFF", 64, 0, 3.0],
                ["NOTE_ON", 65, 65, 4.0],  # Slight variation
                ["NOTE_OFF", 65, 0, 5.0]
            ]
        }
        
        token_data = self._create_token_data([neutral_section])
        result = classify_momentum_from_tokens(token_data)
        
        self.assertFalse(result.get("error", True))
        momentum = result["momentum"][0]
        self.assertEqual(momentum["label"], "neutral")
        self.assertGreaterEqual(momentum["score"], 0.35)
        self.assertLessEqual(momentum["score"], 0.65)
    
    def test_pitch_slope_calculation(self):
        """Test pitch slope calculation from token sequences."""
        # Rising pitch sequence
        rising_tokens = [
            ["NOTE_ON", 60, 80, 0.0],
            ["NOTE_ON", 62, 80, 1.0],
            ["NOTE_ON", 64, 80, 2.0],
            ["NOTE_ON", 67, 80, 3.0]
        ]
        
        rising_slope = _calculate_pitch_slope(rising_tokens)
        self.assertGreater(rising_slope, 0)
        
        # Falling pitch sequence
        falling_tokens = [
            ["NOTE_ON", 72, 80, 0.0],
            ["NOTE_ON", 69, 80, 1.0],
            ["NOTE_ON", 65, 80, 2.0],
            ["NOTE_ON", 60, 80, 3.0]
        ]
        
        falling_slope = _calculate_pitch_slope(falling_tokens)
        self.assertLess(falling_slope, 0)
        
        # Stable pitch sequence
        stable_tokens = [
            ["NOTE_ON", 64, 80, 0.0],
            ["NOTE_ON", 64, 80, 1.0],
            ["NOTE_ON", 64, 80, 2.0]
        ]
        
        stable_slope = _calculate_pitch_slope(stable_tokens)
        self.assertEqual(stable_slope, 0.0)
    
    def test_empty_token_sequence(self):
        """Test handling of empty token sequences."""
        empty_section = {
            "metadata": {
                "avg_bpm": 120.0,
                "avg_velocity": 0.0,  # No notes
                "note_count": 0
            },
            "token_sequence": []
        }
        
        token_data = self._create_token_data([empty_section])
        result = classify_momentum_from_tokens(token_data)
        
        self.assertFalse(result.get("error", True))
        momentum = result["momentum"][0]
        
        # Should still produce a classification
        self.assertIn(momentum["label"], ["positive", "negative", "neutral"])
        self.assertEqual(momentum["components"]["pitch_slope"], 0.0)
    
    def test_multiple_sections_classification(self):
        """Test classification of multiple sections."""
        sections = [
            {  # Positive
                "metadata": {"avg_bpm": 140.0, "avg_velocity": 90.0, "note_count": 12},
                "token_sequence": [
                    ["NOTE_ON", 60, 90, 0.0],
                    ["NOTE_ON", 67, 90, 2.0],
                    ["NOTE_ON", 72, 90, 4.0]
                ]
            },
            {  # Negative
                "metadata": {"avg_bpm": 80.0, "avg_velocity": 40.0, "note_count": 4},
                "token_sequence": [
                    ["NOTE_ON", 70, 40, 0.0],  
                    ["NOTE_ON", 65, 40, 2.0],
                    ["NOTE_ON", 60, 40, 4.0]
                ]
            },
            {  # Neutral
                "metadata": {"avg_bpm": 115.0, "avg_velocity": 65.0, "note_count": 8},
                "token_sequence": [
                    ["NOTE_ON", 64, 65, 0.0],
                    ["NOTE_ON", 64, 65, 2.0]
                ]
            }
        ]
        
        token_data = self._create_token_data(sections)
        result = classify_momentum_from_tokens(token_data)
        
        self.assertFalse(result.get("error", True))
        self.assertEqual(len(result["momentum"]), 3)
        
        labels = [m["label"] for m in result["momentum"]]
        self.assertIn("positive", labels)
        self.assertIn("negative", labels) 
        self.assertIn("neutral", labels)
    
    def test_momentum_distribution_analysis(self):
        """Test momentum distribution analysis."""
        # Create result with mixed momentum
        momentum_data = {
            "error": False,
            "tenant_id": self.tenant_id,
            "file_id": self.file_id,
            "total_sections": 4,
            "momentum": [
                {"section_id": "s1", "label": "positive", "score": 0.8},
                {"section_id": "s2", "label": "positive", "score": 0.7},
                {"section_id": "s3", "label": "negative", "score": 0.2},
                {"section_id": "s4", "label": "neutral", "score": 0.5}
            ]
        }
        
        analysis = analyze_momentum_distribution(momentum_data)
        
        self.assertEqual(analysis["total_sections"], 4)
        self.assertEqual(analysis["label_distribution"]["positive"]["count"], 2)
        self.assertEqual(analysis["label_distribution"]["negative"]["count"], 1)
        self.assertEqual(analysis["label_distribution"]["neutral"]["count"], 1)
        self.assertEqual(analysis["dominant_momentum"], "positive")
        self.assertTrue(analysis["momentum_variance"])  # Should be True for mixed momentum
        
        # Check score statistics
        scores = [0.8, 0.7, 0.2, 0.5]
        expected_mean = sum(scores) / len(scores)
        self.assertAlmostEqual(analysis["score_statistics"]["mean"], expected_mean, places=2)
    
    def test_error_passthrough(self):
        """Test that input errors are passed through."""
        error_data = {
            "error": True,
            "tenant_id": self.tenant_id,
            "message": "Test error"
        }
        
        result = classify_momentum_from_tokens(error_data)
        
        self.assertTrue(result.get("error", False))
        self.assertEqual(result["tenant_id"], self.tenant_id)
        self.assertEqual(result["message"], "Test error")
    
    def test_no_tokens_error(self):
        """Test handling when no tokens are provided."""
        no_tokens_data = {
            "error": False,
            "tenant_id": self.tenant_id,
            "file_id": self.file_id,
            "total_sections": 0,
            "tokens": []
        }
        
        result = classify_momentum_from_tokens(no_tokens_data)
        
        self.assertTrue(result.get("error", False))
        self.assertEqual(result["tenant_id"], self.tenant_id)
    
    def test_score_components_calculation(self):
        """Test that score components are calculated correctly."""
        section = {
            "metadata": {
                "avg_bpm": 120.0,  # (120-60)/100 = 0.6 tempo_norm
                "avg_velocity": 80.0,  # 80/100 = 0.8 vel_norm
                "note_count": 4
            },
            "token_sequence": [
                ["NOTE_ON", 60, 80, 0.0],
                ["NOTE_ON", 65, 80, 2.0]  # Slight rise, should give positive slope
            ]
        }
        
        token_data = self._create_token_data([section])
        result = classify_momentum_from_tokens(token_data)
        
        momentum = result["momentum"][0]
        components = momentum["components"]
        
        # Check individual components
        self.assertAlmostEqual(components["tempo_norm"], 0.6, places=2)
        self.assertAlmostEqual(components["velocity_norm"], 0.8, places=2)
        self.assertGreater(components["pitch_slope_norm"], 0.5)  # Rising pitch
        
        # Check overall score calculation
        expected_score = 0.4 * 0.6 + 0.4 * 0.8 + 0.2 * components["pitch_slope_norm"]
        self.assertAlmostEqual(momentum["score"], expected_score, places=2)


if __name__ == "__main__":
    unittest.main()