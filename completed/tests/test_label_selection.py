"""
Unit tests for label-based motif selection.
"""

import json
import unittest
import tempfile
from pathlib import Path
import sys
import os
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from motif_selector import (
    decide_label_from_metrics,
    _evaluate_conditions,
    select_motifs_by_label,
    get_training_stats
)


class TestLabelSelection(unittest.TestCase):
    """Test label-based motif selection functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.tenant_id = "test_tenant"
        
        # Create test YAML rules
        self.test_rules = {
            "rules": [
                {
                    "when": {"ctr": ">=0.7", "position": ">=0.8", "clicks": ">=0.6"},
                    "choose_label": "MOMENTUM_POS",
                    "description": "High performance metrics"
                },
                {
                    "when": {"ctr": "<0.3", "position": "<0.4"},
                    "choose_label": "MOMENTUM_NEG",
                    "description": "Poor performance"
                },
                {
                    "when": {"volatility_index": ">=0.6"},
                    "choose_label": "VOLATILE_SPIKE",
                    "description": "High volatility"
                },
                {
                    "when": {"mode": "gsc", "impressions": ">=0.8"},
                    "choose_label": "VOLATILE_SPIKE",
                    "description": "GSC high impressions"
                },
                {
                    "when": {},
                    "choose_label": "NEUTRAL",
                    "description": "Default fallback"
                }
            ],
            "valid_labels": ["MOMENTUM_POS", "MOMENTUM_NEG", "VOLATILE_SPIKE", "NEUTRAL"]
        }
        
        # Write test rules to file
        self.rules_path = os.path.join(self.temp_dir, "test_rules.yaml")
        import yaml
        with open(self.rules_path, 'w') as f:
            yaml.dump(self.test_rules, f)
        
        # Create test catalog with labeled motifs
        self.test_catalog = {
            "total_motifs": 6,
            "motifs": [
                {
                    "id": "motif_1",
                    "label": "MOMENTUM_POS",
                    "metadata": {"note_count": 4}
                },
                {
                    "id": "motif_2", 
                    "label": "MOMENTUM_POS",
                    "metadata": {"note_count": 6}
                },
                {
                    "id": "motif_3",
                    "label": "MOMENTUM_NEG",
                    "metadata": {"note_count": 2}
                },
                {
                    "id": "motif_4",
                    "label": "VOLATILE_SPIKE",
                    "metadata": {"note_count": 8}
                },
                {
                    "id": "motif_5",
                    "label": "NEUTRAL",
                    "metadata": {"note_count": 5}
                },
                {
                    "id": "motif_6",
                    "label": "UNLABELED",
                    "metadata": {"note_count": 3}
                }
            ]
        }
        
        self.catalog_path = os.path.join(self.temp_dir, "test_catalog.json")
        with open(self.catalog_path, 'w') as f:
            json.dump(self.test_catalog, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_positive_momentum_rule(self):
        """Test positive momentum label decision."""
        metrics = {
            "ctr": 0.8,
            "position": 0.9,
            "clicks": 0.7,
            "impressions": 0.6
        }
        
        label = decide_label_from_metrics(metrics, "serp", self.rules_path)
        self.assertEqual(label, "MOMENTUM_POS")
    
    def test_negative_momentum_rule(self):
        """Test negative momentum label decision."""
        metrics = {
            "ctr": 0.2,
            "position": 0.3,
            "clicks": 0.1,
            "impressions": 0.4
        }
        
        label = decide_label_from_metrics(metrics, "serp", self.rules_path)
        self.assertEqual(label, "MOMENTUM_NEG")
    
    def test_volatile_spike_rule(self):
        """Test volatile spike label decision."""
        metrics = {
            "ctr": 0.5,
            "position": 0.6,
            "clicks": 0.4,
            "volatility_index": 0.7
        }
        
        label = decide_label_from_metrics(metrics, "serp", self.rules_path)
        self.assertEqual(label, "VOLATILE_SPIKE")
    
    def test_mode_specific_rule(self):
        """Test mode-specific rule matching."""
        metrics = {
            "ctr": 0.4,
            "position": 0.5,
            "impressions": 0.85,  # High impressions
            "clicks": 0.3
        }
        
        # Should trigger GSC-specific rule
        label = decide_label_from_metrics(metrics, "gsc", self.rules_path)
        self.assertEqual(label, "VOLATILE_SPIKE")
        
        # Same metrics with SERP mode should fall through to default
        label = decide_label_from_metrics(metrics, "serp", self.rules_path)
        self.assertEqual(label, "NEUTRAL")
    
    def test_neutral_fallback_rule(self):
        """Test that neutral fallback works."""
        metrics = {
            "ctr": 0.5,
            "position": 0.6,
            "clicks": 0.4,
            "impressions": 0.5
        }
        
        label = decide_label_from_metrics(metrics, "serp", self.rules_path)
        self.assertEqual(label, "NEUTRAL")
    
    def test_evaluate_conditions(self):
        """Test condition evaluation logic."""
        metrics = {"ctr": 0.8, "position": 0.9}
        
        # Test various comparison operators
        self.assertTrue(_evaluate_conditions(metrics, {"ctr": ">=0.7"}))
        self.assertFalse(_evaluate_conditions(metrics, {"ctr": ">=0.9"}))
        
        self.assertTrue(_evaluate_conditions(metrics, {"ctr": ">0.7"}))
        self.assertFalse(_evaluate_conditions(metrics, {"ctr": ">0.8"}))
        
        self.assertTrue(_evaluate_conditions(metrics, {"position": "<=0.9"}))
        self.assertFalse(_evaluate_conditions(metrics, {"position": "<=0.8"}))
        
        self.assertTrue(_evaluate_conditions(metrics, {"position": "<1.0"}))
        self.assertFalse(_evaluate_conditions(metrics, {"position": "<0.9"}))
        
        # Test multiple conditions (AND logic)
        self.assertTrue(_evaluate_conditions(metrics, {"ctr": ">=0.7", "position": ">=0.8"}))
        self.assertFalse(_evaluate_conditions(metrics, {"ctr": ">=0.7", "position": ">=0.95"}))
        
        # Test empty conditions (should match anything)
        self.assertTrue(_evaluate_conditions(metrics, {}))
        
        # Test missing metric
        self.assertFalse(_evaluate_conditions(metrics, {"missing_metric": ">=0.5"}))
    
    def test_string_equality_conditions(self):
        """Test string equality conditions for mode matching."""
        metrics = {"mode": "gsc", "ctr": 0.5}
        
        self.assertTrue(_evaluate_conditions(metrics, {"mode": "gsc"}))
        self.assertFalse(_evaluate_conditions(metrics, {"mode": "serp"}))
        self.assertTrue(_evaluate_conditions(metrics, {"mode": "==gsc"}))
        self.assertFalse(_evaluate_conditions(metrics, {"mode": "==serp"}))
    
    def test_select_motifs_by_label_matching(self):
        """Test motif selection based on label matching."""
        metrics = {
            "ctr": 0.8,
            "position": 0.9,
            "clicks": 0.7
        }
        
        # Should select MOMENTUM_POS motifs
        selected = select_motifs_by_label(
            metrics, "serp", self.tenant_id, num_motifs=2,
            catalog_path=self.catalog_path, rules_path=self.rules_path
        )
        
        self.assertEqual(len(selected), 2)
        # Should get both MOMENTUM_POS motifs
        selected_labels = [m["label"] for m in selected]
        self.assertTrue(all(label == "MOMENTUM_POS" for label in selected_labels))
    
    def test_select_motifs_fallback_to_unlabeled(self):
        """Test fallback to unlabeled motifs when not enough labeled ones."""
        metrics = {
            "volatility_index": 0.7  # Should trigger VOLATILE_SPIKE
        }
        
        # Only 1 VOLATILE_SPIKE motif, but asking for 3
        selected = select_motifs_by_label(
            metrics, "serp", self.tenant_id, num_motifs=3,
            catalog_path=self.catalog_path, rules_path=self.rules_path
        )
        
        self.assertEqual(len(selected), 3)
        # Should include the VOLATILE_SPIKE motif plus unlabeled ones
        selected_labels = [m["label"] for m in selected]
        self.assertIn("VOLATILE_SPIKE", selected_labels)
    
    def test_get_training_stats(self):
        """Test training statistics calculation."""
        stats = get_training_stats(self.catalog_path)
        
        self.assertEqual(stats["total_motifs"], 6)
        self.assertEqual(stats["labeled_motifs"], 5)  # 6 total - 1 unlabeled
        self.assertTrue(stats["training_ready"])
        self.assertAlmostEqual(stats["coverage_percent"], 83.3, places=1)
        
        # Check label distribution
        expected_counts = {
            "MOMENTUM_POS": 2,
            "MOMENTUM_NEG": 1,
            "VOLATILE_SPIKE": 1,
            "NEUTRAL": 1,
            "UNLABELED": 1
        }
        self.assertEqual(stats["label_distribution"]["counts"], expected_counts)
    
    def test_edge_case_no_motifs(self):
        """Test behavior with empty catalog."""
        empty_catalog = {"total_motifs": 0, "motifs": []}
        empty_catalog_path = os.path.join(self.temp_dir, "empty_catalog.json")
        
        with open(empty_catalog_path, 'w') as f:
            json.dump(empty_catalog, f)
        
        metrics = {"ctr": 0.8, "position": 0.9}
        selected = select_motifs_by_label(
            metrics, "serp", self.tenant_id, num_motifs=4,
            catalog_path=empty_catalog_path, rules_path=self.rules_path
        )
        
        # Should return fallback motifs
        self.assertEqual(len(selected), 4)
        self.assertTrue(all("fallback" in m["id"] for m in selected))
    
    def test_deterministic_selection(self):
        """Test that selection is deterministic for same inputs."""
        metrics = {"ctr": 0.5, "position": 0.6}
        
        # Run selection multiple times with same inputs
        selected1 = select_motifs_by_label(
            metrics, "serp", self.tenant_id, num_motifs=2,
            catalog_path=self.catalog_path, rules_path=self.rules_path
        )
        
        selected2 = select_motifs_by_label(
            metrics, "serp", self.tenant_id, num_motifs=2,
            catalog_path=self.catalog_path, rules_path=self.rules_path
        )
        
        # Should get same motifs in same order
        self.assertEqual([m["id"] for m in selected1], [m["id"] for m in selected2])
    
    def test_different_tenants_different_selection(self):
        """Test that different tenants get different selections."""
        metrics = {"ctr": 0.5, "position": 0.6}
        
        selected1 = select_motifs_by_label(
            metrics, "serp", "tenant_a", num_motifs=2,
            catalog_path=self.catalog_path, rules_path=self.rules_path
        )
        
        selected2 = select_motifs_by_label(
            metrics, "serp", "tenant_b", num_motifs=2,
            catalog_path=self.catalog_path, rules_path=self.rules_path
        )
        
        # Different tenants should get different selections (with high probability)
        # This might occasionally fail due to randomness, but should usually pass
        selected_ids1 = [m["id"] for m in selected1]
        selected_ids2 = [m["id"] for m in selected2]
        
        # At least one motif should be different
        self.assertNotEqual(selected_ids1, selected_ids2)


if __name__ == "__main__":
    unittest.main()