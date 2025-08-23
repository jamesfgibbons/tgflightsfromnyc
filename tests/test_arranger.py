"""
Unit tests for music arranger functionality.
"""

import pytest
from src.arranger import MusicArranger, Key, SectionType


class TestMusicArranger:
    """Test musical arrangement and default section building."""
    
    def test_build_default_sections_covers_total_bars(self):
        """Test that default sections cover the specified total bars."""
        arranger = MusicArranger(total_bars=32)
        
        for total_bars in [8, 16, 24, 32, 48]:
            sections = arranger.build_default_sections(total_bars)
            
            # Should have at least 1 section
            assert len(sections) >= 1
            
            # Total bars should match exactly
            actual_bars = sum(section.bars for section in sections)
            assert actual_bars == total_bars
            
            # All sections should have positive bar counts
            for section in sections:
                assert section.bars > 0
                
    def test_build_default_sections_small_total(self):
        """Test default sections with very small bar counts."""
        arranger = MusicArranger()
        
        # Test with minimal bars
        sections = arranger.build_default_sections(4)
        assert len(sections) >= 1
        assert sum(section.bars for section in sections) == 4
        
        # Should still produce intro at minimum
        assert sections[0].section_type == SectionType.INTRO
        
    def test_build_default_sections_properties(self):
        """Test that default sections have consistent properties."""
        arranger = MusicArranger()
        sections = arranger.build_default_sections(16)
        
        for i, section in enumerate(sections):
            # Each section should have proper properties
            assert isinstance(section.section_type, SectionType)
            assert section.key == Key.C_MAJOR  # Default key
            assert section.tempo == arranger.base_tempo
            assert section.momentum_score == 0.5  # Neutral
            assert section.bars > 0
            
            # Start bars should be sequential
            if i > 0:
                expected_start = sum(s.bars for s in sections[:i])
                assert section.start_bar == expected_start
                
    def test_arrange_momentum_data_empty_fallback(self):
        """Test that empty momentum data falls back to defaults."""
        arranger = MusicArranger(total_bars=24)
        
        # Test with None
        sections = arranger.arrange_momentum_data(None)
        assert len(sections) >= 1
        assert sum(section.bars for section in sections) == 24
        
        # Test with empty list
        sections = arranger.arrange_momentum_data([])
        assert len(sections) >= 1
        assert sum(section.bars for section in sections) == 24
        
    def test_arrange_momentum_data_single_point_fallback(self):
        """Test that single momentum point falls back to defaults."""
        arranger = MusicArranger(total_bars=16)
        
        single_momentum = [{"label": "MOMENTUM_POS", "ctr": 0.8}]
        sections = arranger.arrange_momentum_data(single_momentum)
        
        # Should fallback to defaults with single point
        assert len(sections) >= 1
        assert sum(section.bars for section in sections) == 16
        
    def test_arrange_momentum_data_two_points_produces_sections(self):
        """Test that two momentum bands produce at least 3 musical sections."""
        arranger = MusicArranger(total_bars=32)
        
        two_momentum = [
            {"label": "MOMENTUM_POS", "ctr": 0.8},
            {"label": "MOMENTUM_NEG", "ctr": 0.2}
        ]
        
        sections = arranger.arrange_momentum_data(two_momentum)
        
        # Should produce at least 3 sections
        assert len(sections) >= 3
        
        # Should cover all bars
        assert sum(section.bars for section in sections) == 32
        
        # Should have varied momentum scores based on input
        momentum_scores = [section.momentum_score for section in sections]
        assert len(set(momentum_scores)) >= 2  # At least 2 different scores
        
    def test_arrange_momentum_data_sufficient_data(self):
        """Test arrangement with sufficient momentum data."""
        arranger = MusicArranger(total_bars=32)
        
        momentum_data = [
            {"label": "MOMENTUM_POS", "ctr": 0.9, "position": 0.8},
            {"label": "NEUTRAL", "ctr": 0.5, "position": 0.5},
            {"label": "MOMENTUM_NEG", "ctr": 0.2, "position": 0.3},
            {"label": "VOLATILE_SPIKE", "ctr": 0.7, "position": 0.6},
            {"label": "MOMENTUM_POS", "ctr": 0.8, "position": 0.9}
        ]
        
        sections = arranger.arrange_momentum_data(momentum_data)
        
        # Should use momentum data, not defaults
        assert len(sections) == 5  # All section types
        assert sum(section.bars for section in sections) == 32
        
        # Should have different keys based on momentum
        keys = [section.key for section in sections]
        assert len(set(keys)) >= 2  # Should have varied keys
        
        # Should have different momentum scores
        momentum_scores = [section.momentum_score for section in sections]
        assert len(set(momentum_scores)) >= 2
        
    def test_arrange_momentum_data_section_distribution(self):
        """Test that momentum data is properly distributed across sections."""
        arranger = MusicArranger(total_bars=20)
        
        # Test with exactly 2 momentum points
        two_points = [
            {"label": "MOMENTUM_POS", "ctr": 0.9},
            {"label": "MOMENTUM_NEG", "ctr": 0.1}
        ]
        
        sections = arranger.arrange_momentum_data(two_points)
        
        # First few sections should use first momentum point (higher score)
        # Later sections should use second momentum point (lower score)
        early_scores = [s.momentum_score for s in sections[:2]]
        late_scores = [s.momentum_score for s in sections[-2:]]
        
        assert any(score > 0.7 for score in early_scores), "Early sections should have high momentum"
        assert any(score < 0.3 for score in late_scores), "Late sections should have low momentum"
        
    def test_section_types_order(self):
        """Test that sections maintain proper order."""
        arranger = MusicArranger(total_bars=32)
        
        momentum_data = [{"label": "NEUTRAL", "ctr": 0.5}] * 5
        sections = arranger.arrange_momentum_data(momentum_data)
        
        expected_order = [
            SectionType.INTRO,
            SectionType.BODY_A, 
            SectionType.BRIDGE,
            SectionType.BODY_B,
            SectionType.OUTRO
        ]
        
        for i, section in enumerate(sections):
            if i < len(expected_order):
                assert section.section_type == expected_order[i]
                
    def test_bar_allocation_consistency(self):
        """Test that bar allocation is consistent across different inputs."""
        arranger = MusicArranger(total_bars=16)
        
        # Different inputs should produce same total bar allocation
        inputs = [
            [{"label": "MOMENTUM_POS"}] * 3,
            [{"label": "MOMENTUM_NEG"}] * 4, 
            [{"label": "NEUTRAL"}] * 5
        ]
        
        for momentum_data in inputs:
            sections = arranger.arrange_momentum_data(momentum_data)
            total_bars = sum(section.bars for section in sections)
            assert total_bars == 16, f"Total bars should be 16, got {total_bars}"