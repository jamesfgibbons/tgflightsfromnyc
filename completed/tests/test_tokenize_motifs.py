"""
Unit tests for tokenize_motifs.py
"""

import json
import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tokenize_motifs import tokenize_motifs_from_bars, _create_section_hash, _create_token_sequence


class TestTokenizeMotifs(unittest.TestCase):
    """Test motif tokenization functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tenant_id = "test_tenant"
        self.file_id = "test_file"
        
        # Create sample bar data
        self.sample_bars_data = {
            "error": False,
            "tenant_id": self.tenant_id,
            "file_id": self.file_id,
            "total_bars": 8,
            "bars": [
                {
                    "bar_index": 0,
                    "time_signature": "4/4",
                    "start_sec": 0.0,
                    "end_sec": 2.0,
                    "bpm": 120.0,
                    "notes": [
                        {"pitch": 60, "velocity": 80, "start": 0.0, "duration": 1.0},
                        {"pitch": 64, "velocity": 80, "start": 1.0, "duration": 1.0}
                    ],
                    "hash": "bar0hash"
                },
                {
                    "bar_index": 1,
                    "time_signature": "4/4",
                    "start_sec": 2.0,
                    "end_sec": 4.0,
                    "bpm": 120.0,
                    "notes": [
                        {"pitch": 67, "velocity": 90, "start": 0.0, "duration": 0.5},
                        {"pitch": 72, "velocity": 90, "start": 0.5, "duration": 1.5}
                    ],
                    "hash": "bar1hash"
                },
                {
                    "bar_index": 2,
                    "time_signature": "4/4",
                    "start_sec": 4.0,
                    "end_sec": 6.0,
                    "bpm": 120.0,
                    "notes": [
                        {"pitch": 60, "velocity": 80, "start": 0.0, "duration": 1.0},
                        {"pitch": 64, "velocity": 80, "start": 1.0, "duration": 1.0}
                    ],
                    "hash": "bar2hash"
                },
                {
                    "bar_index": 3,
                    "time_signature": "4/4",
                    "start_sec": 6.0,
                    "end_sec": 8.0,
                    "bpm": 120.0,
                    "notes": [
                        {"pitch": 67, "velocity": 90, "start": 0.0, "duration": 0.5},
                        {"pitch": 72, "velocity": 90, "start": 0.5, "duration": 1.5}
                    ],
                    "hash": "bar3hash"
                },
                # Repeat pattern for bars 4-7
                {
                    "bar_index": 4,
                    "time_signature": "4/4",
                    "start_sec": 8.0,
                    "end_sec": 10.0,
                    "bpm": 120.0,
                    "notes": [
                        {"pitch": 60, "velocity": 80, "start": 0.0, "duration": 1.0},
                        {"pitch": 64, "velocity": 80, "start": 1.0, "duration": 1.0}
                    ],
                    "hash": "bar4hash"
                },
                {
                    "bar_index": 5,
                    "time_signature": "4/4",
                    "start_sec": 10.0,
                    "end_sec": 12.0,
                    "bpm": 120.0,
                    "notes": [
                        {"pitch": 67, "velocity": 90, "start": 0.0, "duration": 0.5},
                        {"pitch": 72, "velocity": 90, "start": 0.5, "duration": 1.5}
                    ],
                    "hash": "bar5hash"
                },
                {
                    "bar_index": 6,
                    "time_signature": "4/4",
                    "start_sec": 12.0,
                    "end_sec": 14.0,
                    "bpm": 120.0,
                    "notes": [
                        {"pitch": 60, "velocity": 80, "start": 0.0, "duration": 1.0},
                        {"pitch": 64, "velocity": 80, "start": 1.0, "duration": 1.0}
                    ],
                    "hash": "bar6hash"
                },
                {
                    "bar_index": 7,
                    "time_signature": "4/4",
                    "start_sec": 14.0,
                    "end_sec": 16.0,
                    "bpm": 120.0,
                    "notes": [
                        {"pitch": 67, "velocity": 90, "start": 0.0, "duration": 0.5},
                        {"pitch": 72, "velocity": 90, "start": 0.5, "duration": 1.5}
                    ],
                    "hash": "bar7hash"
                }
            ]
        }
    
    def test_tokenize_basic_sections(self):
        """Test basic tokenization into sections."""
        result = tokenize_motifs_from_bars(self.sample_bars_data, section_size=4)
        
        # Verify basic structure
        self.assertFalse(result.get("error", True))
        self.assertEqual(result["tenant_id"], self.tenant_id)
        self.assertEqual(result["file_id"], self.file_id)
        self.assertIn("tokens", result)
        
        # Should have 2 sections (8 bars / 4 per section)
        self.assertEqual(result["total_sections"], 2)
        self.assertEqual(len(result["tokens"]), 2)
        
        # Check section structure
        first_section = result["tokens"][0]
        required_fields = ["section_id", "hash", "bars_covered", "start_bar", "end_bar", "token_sequence", "metadata"]
        for field in required_fields:
            self.assertIn(field, first_section)
        
        # Verify section spans correct bars
        self.assertEqual(first_section["start_bar"], 0)
        self.assertEqual(first_section["end_bar"], 3)
    
    def test_token_sequence_format(self):
        """Test that token sequences have correct format."""
        result = tokenize_motifs_from_bars(self.sample_bars_data, section_size=4)
        
        first_section = result["tokens"][0]
        token_sequence = first_section["token_sequence"]
        
        # Should have tokens
        self.assertGreater(len(token_sequence), 0)
        
        # Each token should be [type, pitch, velocity, time]
        for token in token_sequence:
            self.assertEqual(len(token), 4)
            self.assertIn(token[0], ["NOTE_ON", "NOTE_OFF"])
            self.assertIsInstance(token[1], int)  # pitch
            self.assertIsInstance(token[2], int)  # velocity
            self.assertIsInstance(token[3], (int, float))  # time
    
    def test_deduplication_identical_sections(self):
        """Test that identical sections are deduplicated."""
        # Create data with identical patterns in both sections
        identical_bars_data = {
            "error": False,
            "tenant_id": self.tenant_id,
            "file_id": self.file_id,
            "total_bars": 8,
            "bars": []
        }
        
        # Create identical pattern repeated
        base_bar = {
            "bar_index": 0,
            "time_signature": "4/4",
            "start_sec": 0.0,
            "end_sec": 2.0,
            "bpm": 120.0,
            "notes": [
                {"pitch": 60, "velocity": 80, "start": 0.0, "duration": 1.0}
            ],
            "hash": "samehash"
        }
        
        # Create 8 identical bars (will make 2 identical sections)
        for i in range(8):
            bar = base_bar.copy()
            bar["bar_index"] = i
            bar["start_sec"] = i * 2.0
            bar["end_sec"] = (i + 1) * 2.0
            identical_bars_data["bars"].append(bar)
        
        result = tokenize_motifs_from_bars(identical_bars_data, section_size=4)
        
        # Should have 2 total sections but only 1 unique
        self.assertEqual(result["total_sections"], 2)
        self.assertEqual(result["unique_sections"], 1)  # Deduplicated
        self.assertEqual(len(result["tokens"]), 1)
    
    def test_section_hash_consistency(self):
        """Test that section hashes are consistent for identical content."""
        bars1 = [
            {
                "bar_index": 0,
                "notes": [{"pitch": 60, "velocity": 80, "start": 0.0, "duration": 1.0}]
            }
        ]
        
        bars2 = [
            {
                "bar_index": 1,  # Different index
                "notes": [{"pitch": 60, "velocity": 80, "start": 0.0, "duration": 1.0}]  # Same notes
            }
        ]
        
        tokens1 = _create_token_sequence(bars1)
        tokens2 = _create_token_sequence(bars2)
        
        hash1 = _create_section_hash(tokens1)
        hash2 = _create_section_hash(tokens2)
        
        # Hashes should be identical for same musical content
        self.assertEqual(hash1, hash2)
    
    def test_empty_bars_handling(self):
        """Test handling of empty bars (no notes)."""
        empty_bars_data = {
            "error": False,
            "tenant_id": self.tenant_id,
            "file_id": self.file_id,
            "total_bars": 4,
            "bars": [
                {
                    "bar_index": 0,
                    "time_signature": "4/4",
                    "start_sec": 0.0,
                    "end_sec": 2.0,
                    "bpm": 120.0,
                    "notes": [],  # Empty bar
                    "hash": "empty"
                },
                {
                    "bar_index": 1,
                    "time_signature": "4/4",
                    "start_sec": 2.0,
                    "end_sec": 4.0,
                    "bpm": 120.0,
                    "notes": [{"pitch": 60, "velocity": 80, "start": 0.0, "duration": 1.0}],
                    "hash": "nonempty"
                },
                {
                    "bar_index": 2,
                    "time_signature": "4/4",
                    "start_sec": 4.0,
                    "end_sec": 6.0,
                    "bpm": 120.0,
                    "notes": [],  # Empty bar
                    "hash": "empty"
                },
                {
                    "bar_index": 3,
                    "time_signature": "4/4",
                    "start_sec": 6.0,
                    "end_sec": 8.0,
                    "bpm": 120.0,
                    "notes": [],  # Empty bar
                    "hash": "empty"
                }
            ]
        }
        
        result = tokenize_motifs_from_bars(empty_bars_data, section_size=4)
        
        self.assertFalse(result.get("error", True))
        self.assertEqual(len(result["tokens"]), 1)
        
        # Check that bars_covered only counts non-empty bars
        section = result["tokens"][0]
        self.assertEqual(section["bars_covered"], 1)  # Only 1 bar had notes
    
    def test_error_passthrough(self):
        """Test that input errors are passed through."""
        error_data = {
            "error": True,
            "tenant_id": self.tenant_id,
            "message": "Test error"
        }
        
        result = tokenize_motifs_from_bars(error_data)
        
        self.assertTrue(result.get("error", False))
        self.assertEqual(result["tenant_id"], self.tenant_id)
        self.assertEqual(result["message"], "Test error")
    
    def test_no_bars_error(self):
        """Test handling when no bars are provided."""
        no_bars_data = {
            "error": False,
            "tenant_id": self.tenant_id,
            "file_id": self.file_id,
            "total_bars": 0,
            "bars": []
        }
        
        result = tokenize_motifs_from_bars(no_bars_data)
        
        self.assertTrue(result.get("error", False))
        self.assertEqual(result["tenant_id"], self.tenant_id)
    
    def test_incomplete_section_handling(self):
        """Test handling of incomplete sections at end."""
        # 6 bars with section_size=4 should create 1 complete section + 1 padded section
        incomplete_data = self.sample_bars_data.copy()
        incomplete_data["bars"] = incomplete_data["bars"][:6]  # Only 6 bars
        incomplete_data["total_bars"] = 6
        
        result = tokenize_motifs_from_bars(incomplete_data, section_size=4)
        
        self.assertFalse(result.get("error", True))
        self.assertEqual(len(result["tokens"]), 2)  # Should have 2 sections (1 complete, 1 padded)


if __name__ == "__main__":
    unittest.main()