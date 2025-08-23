"""
Tests for DataForSEO merge functionality.
"""

import pytest
import json
from src.merge import merge_dfs, create_sample_merged_data

def test_merge_fields():
    """Test that merge creates records with required fields."""
    # Test with sample data
    keywords = ["test keyword", "another test"]
    sample_data = create_sample_merged_data(keywords, "example.com")
    
    assert len(sample_data) > 0, "Should generate sample data"
    
    # Check required fields exist
    required_fields = ["keyword", "rank", "domain", "ads_slot", "search_volume", "rich_snippet_type", "ai_overview"]
    for record in sample_data[:5]:  # Check first 5 records
        for field in required_fields:
            assert field in record, f"Field {field} missing from record"
    
    # Check data types
    first_record = sample_data[0]
    assert isinstance(first_record["rank"], int), "Rank should be integer"
    assert isinstance(first_record["search_volume"], int), "Search volume should be integer"
    assert isinstance(first_record["ai_overview"], bool), "AI overview should be boolean"

def test_sample_data_generation():
    """Test sample data generation with domain preference."""
    keywords = ["test keyword"]
    domain = "example.com"
    
    sample_data = create_sample_merged_data(keywords, domain)
    
    # Should have 10 results per keyword (top 10)
    assert len(sample_data) == 10, "Should generate 10 results per keyword"
    
    # Check domain appears in results
    domains = [record["domain"] for record in sample_data]
    assert domain in domains, f"Target domain {domain} should appear in results"
    
    # Check ranks are 1-10
    ranks = [record["rank"] for record in sample_data]
    assert set(ranks) == set(range(1, 11)), "Ranks should be 1-10"

def test_merge_empty_inputs():
    """Test merge function handles empty inputs gracefully."""
    result = merge_dfs([], [], [])
    assert result == [], "Should return empty list for empty inputs"
    
    # Test with None inputs
    result = merge_dfs(None, None, None)
    assert result == [], "Should handle None inputs gracefully"

if __name__ == "__main__":
    pytest.main([__file__]) 