"""
Data preprocessing module for SERP Loop Radio.
Adds rank_delta vs previous day and anomaly detection.
"""

import pandas as pd
import numpy as np
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def add_rank_deltas(df: pd.DataFrame, previous_csv_path: Optional[Path] = None) -> pd.DataFrame:
    """
    Add rank_delta column by comparing with previous day's data.
    
    Args:
        df: Current day's SERP data
        previous_csv_path: Path to previous day's CSV file
        
    Returns:
        DataFrame with rank_delta column added
    """
    df = df.copy()
    
    # Initialize rank_delta with 0
    df['rank_delta'] = 0
    
    if previous_csv_path and previous_csv_path.exists():
        try:
            prev_df = pd.read_csv(previous_csv_path)
            logger.info(f"Loaded previous data from {previous_csv_path}")
            
            # Merge on keyword + domain to compare ranks
            merged = df.merge(
                prev_df[['keyword', 'domain', 'rank_absolute']],
                on=['keyword', 'domain'],
                how='left',
                suffixes=('', '_prev')
            )
            
            # Calculate rank delta (negative = improvement, positive = decline)
            merged['rank_delta'] = merged['rank_absolute'] - merged['rank_absolute_prev'].fillna(0)
            
            # Update original dataframe
            df['rank_delta'] = merged['rank_delta'].fillna(0)
            
            logger.info(f"Calculated rank deltas for {len(df)} records")
            
        except Exception as e:
            logger.warning(f"Could not load previous data: {e}")
            df['rank_delta'] = 0
    else:
        logger.info("No previous data available, setting rank_delta to 0")
    
    return df


def detect_anomalies(df: pd.DataFrame, z_threshold: float = 2.0) -> pd.DataFrame:
    """
    Detect anomalies using z-score analysis per query.
    
    Args:
        df: DataFrame with SERP data
        z_threshold: Z-score threshold for anomaly detection
        
    Returns:
        DataFrame with anomaly column added
    """
    df = df.copy()
    df['anomaly'] = False
    
    # Group by keyword to calculate z-scores within each query
    for keyword in df['keyword'].unique():
        keyword_mask = df['keyword'] == keyword
        keyword_data = df[keyword_mask]
        
        if len(keyword_data) < 3:  # Need minimum data points for z-score
            continue
        
        # Calculate z-scores for rank_delta
        if keyword_data['rank_delta'].std() > 0:
            z_scores = np.abs(
                (keyword_data['rank_delta'] - keyword_data['rank_delta'].mean()) / 
                keyword_data['rank_delta'].std()
            )
            
            # Mark anomalies
            anomaly_mask = z_scores > z_threshold
            df.loc[keyword_mask, 'anomaly'] = anomaly_mask
    
    anomaly_count = df['anomaly'].sum()
    logger.info(f"Detected {anomaly_count} anomalies using z-score threshold {z_threshold}")
    
    return df


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add additional derived features for sonification.
    
    Args:
        df: DataFrame with SERP data
        
    Returns:
        DataFrame with additional features
    """
    df = df.copy()
    
    # Add position groupings
    df['position_group'] = pd.cut(
        df['rank_absolute'], 
        bins=[0, 3, 10, 20, float('inf')], 
        labels=['top3', 'top10', 'top20', 'beyond20']
    )
    
    # Add movement categories
    df['movement_type'] = 'stable'
    df.loc[df['rank_delta'] < -2, 'movement_type'] = 'major_gain'
    df.loc[df['rank_delta'] < 0, 'movement_type'] = 'gain'
    df.loc[df['rank_delta'] > 2, 'movement_type'] = 'major_loss'
    df.loc[df['rank_delta'] > 0, 'movement_type'] = 'loss'
    
    # Add brand indicators
    brand_domain = df.get('BRAND_DOMAIN', 'mybrand.com')  # Could be from env
    df['is_brand'] = df['domain'].str.contains(brand_domain, na=False)
    
    # Add competitive pressure (simplified)
    keyword_counts = df.groupby('keyword').size()
    df['competitive_pressure'] = df['keyword'].map(keyword_counts)
    
    # Normalize share_pct within each keyword
    df['share_pct_normalized'] = df.groupby('keyword')['share_pct'].transform(
        lambda x: (x - x.min()) / (x.max() - x.min()) if x.max() > x.min() else 0
    )
    
    logger.info("Added derived features for enhanced sonification")
    
    return df


def validate_data_quality(df: pd.DataFrame) -> pd.DataFrame:
    """
    Validate and clean data quality issues.
    
    Args:
        df: DataFrame with SERP data
        
    Returns:
        Cleaned DataFrame
    """
    df = df.copy()
    initial_count = len(df)
    
    # Remove rows with missing critical data
    df = df.dropna(subset=['keyword', 'rank_absolute'])
    
    # Cap extreme rank values
    df['rank_absolute'] = df['rank_absolute'].clip(1, 100)
    
    # Ensure share_pct is between 0 and 1
    df['share_pct'] = df['share_pct'].clip(0, 1)
    
    # Fill missing rich_type
    df['rich_type'] = df['rich_type'].fillna('')
    
    # Fill missing segment
    df['segment'] = df['segment'].fillna('Central')
    
    # Ensure numeric columns
    numeric_cols = ['rank_absolute', 'rank_delta', 'share_pct', 'etv']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    final_count = len(df)
    logger.info(f"Data validation: {initial_count} -> {final_count} records")
    
    return df


def preprocess_serp_data(
    df: pd.DataFrame, 
    previous_csv_path: Optional[Path] = None,
    z_threshold: float = 2.0
) -> pd.DataFrame:
    """
    Complete preprocessing pipeline for SERP data.
    
    Args:
        df: Raw SERP data
        previous_csv_path: Path to previous day's CSV
        z_threshold: Anomaly detection threshold
        
    Returns:
        Processed DataFrame ready for sonification
    """
    logger.info("Starting SERP data preprocessing pipeline")
    
    # Step 1: Data quality validation
    df = validate_data_quality(df)
    
    # Step 2: Add rank deltas
    df = add_rank_deltas(df, previous_csv_path)
    
    # Step 3: Detect anomalies
    df = detect_anomalies(df, z_threshold)
    
    # Step 4: Add derived features
    df = add_derived_features(df)
    
    logger.info(f"Preprocessing complete: {len(df)} records ready for sonification")
    
    return df


def save_processed_data(df: pd.DataFrame, output_path: Path) -> None:
    """Save processed data to CSV with backup."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save current data
    df.to_csv(output_path, index=False)
    logger.info(f"Saved processed data to {output_path}")
    
    # Create backup with timestamp
    backup_path = output_path.parent / f"backup_{output_path.stem}_{date.today().isoformat()}.csv"
    df.to_csv(backup_path, index=False)
    logger.info(f"Created backup at {backup_path}")


if __name__ == "__main__":
    # Test preprocessing with sample data
    sample_data = {
        'keyword': ['ai chatbot', 'ai chatbot', 'customer service'],
        'domain': ['openai.com', 'intercom.com', 'zendesk.com'],
        'rank_absolute': [1, 5, 3],
        'rich_type': ['', 'video', ''],
        'share_pct': [0.3, 0.1, 0.2],
        'segment': ['Central', 'West', 'East'],
        'etv': [1000, 200, 500]
    }
    
    test_df = pd.DataFrame(sample_data)
    processed_df = preprocess_serp_data(test_df)
    
    print("Sample processed data:")
    print(processed_df[['keyword', 'domain', 'rank_absolute', 'rank_delta', 'anomaly']].head()) 