"""
Test publisher for SERP Loop Radio live streaming using CSV sample data.
Use this to test the live system without requiring DataForSEO API calls.
"""

import os
import asyncio
import logging
import argparse
from datetime import datetime
from typing import Dict, List
import random

import redis.asyncio as redis
import msgpack
import pandas as pd

from .models import SERPSnapshot
from .mappings import MusicMappings, load_mappings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_CHANNEL = "serp_events"


class TestPublisher:
    """Test publisher using CSV sample data for development and testing."""
    
    def __init__(self, csv_file: str = "data/live_sample.csv"):
        self.csv_file = csv_file
        self.redis_client = None
        self.mappings = load_mappings()
        self.events_published = 0
        
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(REDIS_URL, decode_responses=False)
            await self.redis_client.ping()
            logger.info(f"Connected to Redis at {REDIS_URL}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
    
    def load_sample_data(self) -> pd.DataFrame:
        """Load sample SERP data from CSV."""
        try:
            df = pd.read_csv(self.csv_file)
            logger.info(f"Loaded {len(df)} sample SERP records from {self.csv_file}")
            return df
        except Exception as e:
            logger.error(f"Error loading sample data: {e}")
            raise
    
    def create_note_event_from_row(self, row: pd.Series, simulate_change: bool = False) -> Dict:
        """Create a note event from a CSV row."""
        try:
            # Optionally simulate rank changes for more dynamic testing
            rank_delta = row['rank_delta']
            if simulate_change:
                rank_delta = random.randint(-5, 5)
            
            # Use mapping system to convert to musical parameters
            pitch_adjustment = self.mappings.get_pitch_from_rank_delta(rank_delta)
            base_pitch = 60  # Middle C
            pitch = base_pitch + pitch_adjustment
            pitch = self.mappings.fit_to_scale(pitch, self.mappings.get_scale_notes("C", "pentatonic"))
            
            # Clamp to MIDI range
            pitch = max(0, min(127, pitch))
            
            velocity = self.mappings.get_velocity_from_share(row['share_pct'])
            velocity = max(40, min(127, int(velocity * 127)))
            
            instrument = self.mappings.get_instrument_from_engine(row['engine'])
            
            pan_value = self.mappings.get_pan_from_segment(row['segment'])
            pan = max(-1.0, min(1.0, pan_value / 100.0))
            
            duration = self.mappings.get_duration_from_rich_type(row.get('rich_type', ''))
            duration = max(0.1, min(4.0, duration))
            
            # Detect anomalies
            anomaly = abs(rank_delta) >= 5 or row.get('anomaly', False)
            
            # Check if this is a brand result
            brand_domain = os.getenv('BRAND_DOMAIN', 'mybrand.com')
            brand_rank = row['rank_absolute'] if brand_domain in str(row['domain']) else None
            
            note_event = {
                "event_type": "note_on",
                "pitch": pitch,
                "velocity": velocity,
                "pan": pan,
                "duration": duration,
                "instrument": instrument,
                "channel": 0,
                "keyword": str(row['keyword']),
                "engine": str(row['engine']),
                "domain": str(row['domain']),
                "rank_delta": rank_delta,
                "timestamp": datetime.utcnow().isoformat(),
                "anomaly": anomaly,
                "brand_rank": brand_rank,
                "is_new": False
            }
            
            return note_event
            
        except Exception as e:
            logger.error(f"Error creating note event: {e}")
            return None
    
    async def publish_event(self, event: Dict):
        """Publish a single event to Redis."""
        if not self.redis_client or not event:
            return
        
        try:
            # Serialize event with msgpack
            packed_data = msgpack.packb(event)
            
            # Publish to Redis channel
            await self.redis_client.publish(REDIS_CHANNEL, packed_data)
            
            self.events_published += 1
            
            logger.info(f"Published: {event['keyword']} ({event['domain']}) "
                       f"rank_delta={event['rank_delta']} pitch={event['pitch']}")
            
        except Exception as e:
            logger.error(f"Error publishing event: {e}")
    
    async def simulate_real_time_stream(self, interval: float = 2.0, simulate_changes: bool = True):
        """Simulate real-time SERP events by publishing sample data continuously."""
        logger.info(f"Starting real-time simulation (interval: {interval}s)")
        
        df = self.load_sample_data()
        
        try:
            while True:
                # Pick a random row from the sample data
                row = df.sample(1).iloc[0]
                
                # Create and publish event
                event = self.create_note_event_from_row(row, simulate_change=simulate_changes)
                if event:
                    await self.publish_event(event)
                
                # Wait before next event
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("Simulation stopped by user")
        except Exception as e:
            logger.error(f"Error in simulation: {e}")
    
    async def publish_all_sample_data(self, delay: float = 0.5):
        """Publish all sample data with delay between events."""
        logger.info("Publishing all sample data...")
        
        df = self.load_sample_data()
        
        for _, row in df.iterrows():
            event = self.create_note_event_from_row(row)
            if event:
                await self.publish_event(event)
                await asyncio.sleep(delay)
        
        logger.info(f"Published {self.events_published} events")
    
    async def test_stations(self):
        """Test events for different stations."""
        logger.info("Testing station-specific events...")
        
        # AI Lens station - AI-powered engines
        ai_event = {
            "event_type": "note_on",
            "pitch": 65,
            "velocity": 80,
            "pan": 0.3,
            "duration": 1.5,
            "instrument": 48,
            "channel": 0,
            "keyword": "ai search",
            "engine": "google_ai",
            "domain": "perplexity.ai",
            "rank_delta": -3,
            "timestamp": datetime.utcnow().isoformat(),
            "anomaly": False,
            "brand_rank": None,
            "is_new": False
        }
        
        # Opportunity station - large movement
        opportunity_event = {
            "event_type": "note_on",
            "pitch": 70,
            "velocity": 100,
            "pan": -0.5,
            "duration": 2.0,
            "instrument": 0,
            "channel": 0,
            "keyword": "serp tracking",
            "engine": "google_web",
            "domain": "mybrand.com",
            "rank_delta": -7,  # Large improvement
            "timestamp": datetime.utcnow().isoformat(),
            "anomaly": True,
            "brand_rank": 2,
            "is_new": False
        }
        
        # Daily station - normal change
        daily_event = {
            "event_type": "note_on",
            "pitch": 60,
            "velocity": 70,
            "pan": 0.0,
            "duration": 1.0,
            "instrument": 0,
            "channel": 0,
            "keyword": "marketing tools",
            "engine": "google_web",
            "domain": "hubspot.com",
            "rank_delta": 1,
            "timestamp": datetime.utcnow().isoformat(),
            "anomaly": False,
            "brand_rank": None,
            "is_new": False
        }
        
        events = [ai_event, opportunity_event, daily_event]
        
        for event in events:
            await self.publish_event(event)
            logger.info(f"Published {event['engine']} event for testing")
            await asyncio.sleep(1)


async def main():
    """Main entry point for test publisher."""
    parser = argparse.ArgumentParser(description="SERP Loop Radio Test Publisher")
    parser.add_argument("--mode", choices=["stream", "batch", "stations"], default="stream",
                       help="Publishing mode")
    parser.add_argument("--interval", type=float, default=2.0,
                       help="Interval between events in stream mode (seconds)")
    parser.add_argument("--csv", default="data/live_sample.csv",
                       help="Path to sample CSV file")
    parser.add_argument("--simulate-changes", action="store_true",
                       help="Simulate random rank changes")
    
    args = parser.parse_args()
    
    publisher = TestPublisher(args.csv)
    
    try:
        await publisher.initialize()
        
        if args.mode == "stream":
            logger.info("Starting streaming mode...")
            await publisher.simulate_real_time_stream(args.interval, args.simulate_changes)
        elif args.mode == "batch":
            logger.info("Publishing all sample data...")
            await publisher.publish_all_sample_data()
        elif args.mode == "stations":
            logger.info("Testing station-specific events...")
            await publisher.test_stations()
            
    except KeyboardInterrupt:
        logger.info("Publisher interrupted by user")
    except Exception as e:
        logger.error(f"Publisher error: {e}")
    finally:
        await publisher.close()


if __name__ == "__main__":
    asyncio.run(main()) 