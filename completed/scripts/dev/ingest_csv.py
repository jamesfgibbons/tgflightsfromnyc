#!/usr/bin/env python3
"""
SERP Loop Radio - CSV Ingestion Script

This script uploads sample CSV data to the S3 staging bucket 
to trigger Snowpipe ingestion for testing and development.
"""

import os
import sys
import csv
import boto3
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_sample_csv(output_path: str, num_records: int = 50):
    """Generate sample CSV data for testing."""
    import random
    
    keywords = [
        'sustainable fashion', 'eco friendly products', 'organic clothing',
        'green technology', 'renewable energy', 'electric vehicles',
        'plant based diet', 'zero waste lifestyle', 'solar panels',
        'recycled materials', 'carbon footprint', 'biodegradable packaging',
        'fair trade coffee', 'organic skincare', 'sustainable travel',
        'green building', 'clean energy', 'environmental consulting',
        'organic food delivery', 'eco tourism', 'sustainable investing',
        'green marketing', 'renewable resources', 'climate change solutions',
        'sustainable agriculture', 'green business', 'eco innovation'
    ]
    
    domains = [
        'example.com', 'greentech.com', 'ecosolutions.org', 'sustainablelife.net',
        'cleanenergy.co', 'organicmarket.com', 'ecofriendly.store', 'greenliving.info'
    ]
    
    # Generate data for the last 7 days
    base_date = datetime.now() - timedelta(days=7)
    
    records = []
    for i in range(num_records):
        keyword = random.choice(keywords)
        domain = random.choice(domains)
        
        # Generate realistic ranking data
        current_rank = random.randint(1, 100)
        # Create some ranking movement
        rank_change = random.randint(-15, 15)
        previous_rank = max(1, min(100, current_rank - rank_change))
        rank_delta = current_rank - previous_rank
        
        market_share = random.uniform(0.5, 25.0)
        search_volume = random.randint(100, 10000)
        competition_score = random.uniform(0.1, 1.0)
        
        # Add some time variation
        date_captured = base_date + timedelta(
            days=random.randint(0, 6),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )
        
        record = {
            'query_id': f'demo_{i:03d}',
            'keyword': keyword,
            'domain': domain,
            'current_rank': current_rank,
            'previous_rank': previous_rank,
            'rank_delta': rank_delta,
            'market_share_pct': round(market_share, 2),
            'search_volume': search_volume,
            'competition_score': round(competition_score, 2),
            'date_captured': date_captured.strftime('%Y-%m-%d %H:%M:%S')
        }
        records.append(record)
    
    # Write CSV
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'query_id', 'keyword', 'domain', 'current_rank', 'previous_rank',
            'rank_delta', 'market_share_pct', 'search_volume', 'competition_score',
            'date_captured'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    
    logger.info(f"Generated {num_records} sample records in {output_path}")
    return records

def upload_to_s3(csv_path: str, bucket_name: str, s3_key: str = None):
    """Upload CSV file to S3 staging bucket."""
    if not s3_key:
        filename = Path(csv_path).name
        s3_key = f"uploads/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
    
    try:
        s3_client = boto3.client('s3')
        
        # Upload file
        with open(csv_path, 'rb') as f:
            s3_client.upload_fileobj(
                f, 
                bucket_name, 
                s3_key,
                ExtraArgs={
                    'ContentType': 'text/csv',
                    'Metadata': {
                        'source': 'serp-radio-dev-script',
                        'uploaded_at': datetime.now().isoformat()
                    }
                }
            )
        
        logger.info(f"Uploaded {csv_path} to s3://{bucket_name}/{s3_key}")
        
        # Verify upload
        response = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
        size = response['ContentLength']
        logger.info(f"Upload verified: {size} bytes")
        
        return f"s3://{bucket_name}/{s3_key}"
        
    except Exception as e:
        logger.error(f"Failed to upload to S3: {str(e)}")
        raise

def trigger_snowpipe(pipe_name: str = "SERP_RADIO.MARKET_SHARE.SERP_INGESTION_PIPE"):
    """Trigger Snowpipe to process the uploaded file."""
    try:
        # Note: In production, you'd use the Snowflake Python connector
        # For now, we'll just log the action
        logger.info(f"Snowpipe trigger would be sent to: {pipe_name}")
        logger.info("In production, this would use the Snowflake REST API or Python connector")
        
        # Example of what the actual call would look like:
        """
        import snowflake.connector
        
        conn = snowflake.connector.connect(
            user=os.environ['SNOWFLAKE_USERNAME'],
            password=os.environ['SNOWFLAKE_PASSWORD'],
            account=os.environ['SNOWFLAKE_ACCOUNT'],
        )
        
        cursor = conn.cursor()
        cursor.execute(f"SELECT SYSTEM$PIPE_STATUS('{pipe_name}')")
        status = cursor.fetchone()
        logger.info(f"Pipe status: {status}")
        """
        
    except Exception as e:
        logger.error(f"Failed to trigger Snowpipe: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Ingest CSV data into SERP Loop Radio')
    parser.add_argument('--csv-path', help='Path to existing CSV file')
    parser.add_argument('--generate', action='store_true', help='Generate sample CSV data')
    parser.add_argument('--records', type=int, default=50, help='Number of sample records to generate')
    parser.add_argument('--bucket', default='serp-radio-upload-stage-dev', help='S3 bucket name')
    parser.add_argument('--no-upload', action='store_true', help='Skip S3 upload')
    parser.add_argument('--no-trigger', action='store_true', help='Skip Snowpipe trigger')
    
    args = parser.parse_args()
    
    # Check for required environment variables
    required_env_vars = ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_DEFAULT_REGION']
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    
    if missing_vars and not args.no_upload:
        logger.error(f"Missing required environment variables: {missing_vars}")
        logger.info("Set these variables or use --no-upload to skip S3 upload")
        sys.exit(1)
    
    # Determine CSV file path
    if args.csv_path:
        csv_path = args.csv_path
        if not Path(csv_path).exists():
            logger.error(f"CSV file not found: {csv_path}")
            sys.exit(1)
    elif args.generate:
        csv_path = f"sample_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        generate_sample_csv(csv_path, args.records)
    else:
        logger.error("Either --csv-path or --generate must be specified")
        sys.exit(1)
    
    # Upload to S3
    if not args.no_upload:
        try:
            s3_url = upload_to_s3(csv_path, args.bucket)
            logger.info(f"Successfully uploaded: {s3_url}")
        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
            sys.exit(1)
    else:
        logger.info("Skipping S3 upload")
    
    # Trigger Snowpipe
    if not args.no_trigger:
        try:
            trigger_snowpipe()
        except Exception as e:
            logger.error(f"Snowpipe trigger failed: {str(e)}")
            # Don't exit on Snowpipe failure in dev environment
    else:
        logger.info("Skipping Snowpipe trigger")
    
    logger.info("CSV ingestion process completed successfully!")
    
    # Clean up generated file if it was temporary
    if args.generate and not args.csv_path:
        try:
            os.remove(csv_path)
            logger.info(f"Cleaned up temporary file: {csv_path}")
        except:
            pass

if __name__ == '__main__':
    main() 