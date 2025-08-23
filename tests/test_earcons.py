"""
Unit tests for earcon functionality.
"""

import pytest
from unittest.mock import patch
from src.sonify_service import SonificationService


class TestEarconDetection:
    """Test earcon transition detection."""
    
    def test_detect_positive_transition(self):
        """Test detection of positive momentum transition."""
        service = SonificationService("test-bucket")
        
        momentum_data = {
            "momentum": [
                {"section_id": "section_0", "label": "NEUTRAL"},
                {"section_id": "section_1", "label": "MOMENTUM_POS"},
                {"section_id": "section_2", "label": "MOMENTUM_POS"}
            ]
        }
        
        earcons = service._detect_earcon_triggers(momentum_data)
        
        assert len(earcons) == 1
        assert earcons[0]["type"] == "positive"
        assert earcons[0]["section_id"] == "section_1"
        assert earcons[0]["timing"] == "transition"
    
    def test_detect_negative_transition(self):
        """Test detection of negative momentum transition."""
        service = SonificationService("test-bucket")
        
        momentum_data = {
            "momentum": [
                {"section_id": "section_0", "label": "MOMENTUM_POS"},
                {"section_id": "section_1", "label": "MOMENTUM_NEG"},
            ]
        }
        
        earcons = service._detect_earcon_triggers(momentum_data)
        
        assert len(earcons) == 2  # First positive start + negative transition
        
        # First section positive start
        assert earcons[0]["type"] == "positive"
        assert earcons[0]["section_id"] == "section_0"
        assert earcons[0]["timing"] == "start"
        
        # Transition to negative
        assert earcons[1]["type"] == "negative"
        assert earcons[1]["section_id"] == "section_1"
        assert earcons[1]["timing"] == "transition"
    
    def test_detect_first_section_positive(self):
        """Test detection of positive momentum in first section."""
        service = SonificationService("test-bucket")
        
        momentum_data = {
            "momentum": [
                {"section_id": "section_0", "label": "MOMENTUM_POS"},
                {"section_id": "section_1", "label": "NEUTRAL"}
            ]
        }
        
        earcons = service._detect_earcon_triggers(momentum_data)
        
        assert len(earcons) == 1
        assert earcons[0]["type"] == "positive"
        assert earcons[0]["section_id"] == "section_0"
        assert earcons[0]["timing"] == "start"
    
    def test_no_transitions(self):
        """Test no earcons triggered when no transitions occur."""
        service = SonificationService("test-bucket")
        
        momentum_data = {
            "momentum": [
                {"section_id": "section_0", "label": "NEUTRAL"},
                {"section_id": "section_1", "label": "NEUTRAL"},
                {"section_id": "section_2", "label": "NEUTRAL"}
            ]
        }
        
        earcons = service._detect_earcon_triggers(momentum_data)
        
        assert len(earcons) == 0
    
    def test_multiple_transitions(self):
        """Test multiple transitions trigger multiple earcons."""
        service = SonificationService("test-bucket")
        
        momentum_data = {
            "momentum": [
                {"section_id": "section_0", "label": "MOMENTUM_POS"},  # First positive
                {"section_id": "section_1", "label": "NEUTRAL"},
                {"section_id": "section_2", "label": "MOMENTUM_NEG"},  # Transition to negative
                {"section_id": "section_3", "label": "MOMENTUM_POS"}   # Transition to positive
            ]
        }
        
        earcons = service._detect_earcon_triggers(momentum_data)
        
        assert len(earcons) == 3
        
        # First section positive
        assert earcons[0]["type"] == "positive"
        assert earcons[0]["section_id"] == "section_0"
        assert earcons[0]["timing"] == "start"
        
        # Transition to negative
        assert earcons[1]["type"] == "negative" 
        assert earcons[1]["section_id"] == "section_2"
        assert earcons[1]["timing"] == "transition"
        
        # Transition to positive
        assert earcons[2]["type"] == "positive"
        assert earcons[2]["section_id"] == "section_3"
        assert earcons[2]["timing"] == "transition"