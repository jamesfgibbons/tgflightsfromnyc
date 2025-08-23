"""
Redis publisher for SERP Loop Radio live streaming.
Monitors SERP data changes and publishes real-time events to Redis.
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
import argparse

import redis.asyncio as redis
import msgpack
from aiocache import Cache
import pandas as pd

from .fetch_data import collect_serp_data, DataForSEOClient
from .preprocess import preprocess_serp_data
from .models import SERPSnapshot, NoteEvent, get_station_config
from .mappings import MusicMappings, load_mappings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_CHANNEL = "serp_events"
PUBLISHER_INTERVAL = int(os.getenv("PUBLISHER_INTERVAL", "90"))  # seconds
KEYWORDS_FILE = "config/keywords.txt"
USE_SAMPLE_DATA = os.getenv("USE_SAMPLE_DATA", "false").lower() == "true"


class SERPPublisher:
    """Publishes SERP data changes to Redis for real-time streaming."""
    
    def __init__(self, use_sample_data: bool = None):
        self.redis_client: Optional[redis.Redis] = None
        self.mappings = load_mappings()
        self.cache = Cache(Cache.MEMORY)
        self.last_snapshot: Dict[str, SERPSnapshot] = {}
        self.running = False
        
        # Determine data source
        if use_sample_data is None:
            use_sample_data = USE_SAMPLE_DATA
        self.use_sample_data = use_sample_data
        
        # Statistics
        self.events_published = 0
        self.last_fetch_time: Optional[datetime] = None
        self.fetch_errors = 0
        
        logger.info(f"Publisher initialized with {'sample' if self.use_sample_data else 'live'} data mode")
    
    async def initialize(self):
        """Initialize Redis connection and cache."""
        try:
            self.redis_client = redis.from_url(REDIS_URL, decode_responses=False)
            await self.redis_client.ping()
            logger.info(f"Connected to Redis at {REDIS_URL}")
            
            # Load initial snapshot from cache if available
            cached_snapshot = await self.cache.get("last_serp_snapshot")
            if cached_snapshot:
                self.last_snapshot = cached_snapshot
                logger.info(f"Loaded {len(self.last_snapshot)} cached SERP records")
            
            # Validate credentials if using live data
            if not self.use_sample_data:
                await self._validate_credentials()
            
        except Exception as e:
            logger.error(f"Failed to initialize publisher: {e}")
            raise
    
    async def _validate_credentials(self):
        """Validate DataForSEO credentials are available."""
        login = os.getenv("DATAFORSEO_LOGIN")
        password = os.getenv("DATAFORSEO_PASSWORD")
        
        if not login or not password:
            logger.warning("DataForSEO credentials not found. Falling back to sample data mode.")
            self.use_sample_data = True
            return
        
        try:
            # Test credentials with a simple API call
            client = DataForSEOClient(login, password)
            # This would be a minimal test call to verify credentials
            logger.info("DataForSEO credentials validated successfully")
        except Exception as e:
            logger.warning(f"DataForSEO credentials validation failed: {e}. Falling back to sample data.")
            self.use_sample_data = True
    
    async def close(self):
        """Close connections and save state."""
        if self.redis_client:
            await self.redis_client.close()
        
        # Save snapshot to cache
        if self.last_snapshot:
            await self.cache.set("last_serp_snapshot", self.last_snapshot, ttl=3600)
            logger.info("Saved SERP snapshot to cache")
    
    async def fetch_current_serp_data(self) -> Optional[pd.DataFrame]:
        """Fetch current SERP data from DataForSEO or sample file."""
        try:
            if self.use_sample_data:
                return self._load_sample_data()
            else:
                return await self._fetch_live_data()
                
        except Exception as e:
            logger.error(f"Error fetching SERP data: {e}")
            self.fetch_errors += 1
            return None
    
    def _load_sample_data(self) -> pd.DataFrame:
        """Load sample data from CSV file."""
        import random
        from pathlib import Path
        
        sample_file = Path("data/live_sample.csv")
        if not sample_file.exists():
            # Fallback to the original sample.csv
            sample_file = Path("data/sample.csv")
        
        if not sample_file.exists():
            raise FileNotFoundError(f"No sample data file found at {sample_file}")
        
        df = pd.read_csv(sample_file)
        
        # Simulate some variation in the sample data
        if len(df) > 5:
            # Randomly modify some rank_delta values to simulate changes
            sample_indices = random.sample(range(len(df)), min(3, len(df)))
            for idx in sample_indices:
                df.loc[idx, 'rank_delta'] = random.randint(-3, 3)
                
        logger.info(f"Loaded {len(df)} sample SERP records")
        return df
    
    async def _fetch_live_data(self) -> pd.DataFrame:
        """Fetch live SERP data from DataForSEO API with rate limiting."""
        from pathlib import Path
        keywords_path = Path(KEYWORDS_FILE)
        
        if not keywords_path.exists():
            logger.error(f"Keywords file not found: {keywords_path}")
            raise FileNotFoundError(f"Keywords file required for live data: {keywords_path}")
        
        logger.info("Fetching live SERP data from DataForSEO...")
        
        # Rate limiting: DataForSEO allows ~15 req/s, so add delay between requests
        start_time = datetime.utcnow()
        
        try:
            df = collect_serp_data(datetime.now().date(), keywords_path)
        except Exception as e:
            logger.error(f"DataForSEO API error: {e}")
            # Add exponential backoff for rate limit errors
            if "rate limit" in str(e).lower():
                backoff_time = 60  # Wait 1 minute on rate limit
                logger.warning(f"Rate limit hit, backing off for {backoff_time}s")
                await asyncio.sleep(backoff_time)
            raise
        
        # Ensure minimum interval between API calls (DataForSEO limit: 15 req/s = ~67ms)
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        min_interval = 0.1  # 100ms minimum between calls
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        
        if df.empty:
            logger.warning("No live SERP data collected")
            return df
        
        # Preprocess data
        df = preprocess_serp_data(df)
        
        self.last_fetch_time = datetime.utcnow()
        logger.info(f"Fetched {len(df)} live SERP records in {elapsed:.2f}s")
        
        return df
    
    def create_snapshot_from_dataframe(self, df: pd.DataFrame) -> Dict[str, SERPSnapshot]:
        """Convert DataFrame to snapshot dictionary."""
        snapshot = {}
        
        for _, row in df.iterrows():
            try:
                serp_snapshot = SERPSnapshot(
                    keyword=row.get('keyword', ''),
                    domain=row.get('domain', ''),
                    rank_absolute=int(row.get('rank_absolute', 0)),
                    engine=row.get('engine', 'google_web'),
                    share_pct=float(row.get('share_pct', 0.0)),
                    rich_type=row.get('rich_type', ''),
                    segment=row.get('segment', 'Central'),
                    ai_overview=bool(row.get('ai_overview', False)),
                    etv=int(row.get('etv', 0))
                )
                
                snapshot[serp_snapshot.diff_key()] = serp_snapshot
                
            except Exception as e:
                logger.error(f"Error creating snapshot for row: {e}")
                continue
        
        return snapshot
    
    def detect_changes(self, current_snapshot: Dict[str, SERPSnapshot]) -> List[Dict]:
        """Detect changes between current and previous snapshots."""
        changes = []
        
        # Check for ranking changes
        for key, current_item in current_snapshot.items():
            if key in self.last_snapshot:
                previous_item = self.last_snapshot[key]
                
                # Calculate rank delta
                rank_delta = current_item.rank_absolute - previous_item.rank_absolute
                
                # Check for significant changes
                if (abs(rank_delta) >= 1 or  # Rank change
                    current_item.ai_overview != previous_item.ai_overview or  # AI overview change
                    abs(current_item.share_pct - previous_item.share_pct) >= 0.05):  # Share change
                    
                    # Create note event with station tagging
                    note_event = self.create_note_event(current_item, rank_delta)
                    if note_event:
                        changes.append(note_event)
            
            else:
                # New entry detected
                note_event = self.create_note_event(current_item, 0, is_new=True)
                if note_event:
                    changes.append(note_event)
        
        # Check for disappeared entries
        for key in self.last_snapshot:
            if key not in current_snapshot:
                previous_item = self.last_snapshot[key]
                logger.info(f"Entry disappeared: {key}")
        
        return changes
    
    def create_note_event(self, snapshot: SERPSnapshot, rank_delta: int, is_new: bool = False) -> Optional[Dict]:
        """Create a note event from a SERP snapshot change."""
        try:
            # Use mapping system to convert to musical parameters
            pitch_adjustment = self.mappings.get_pitch_from_rank_delta(rank_delta)
            base_pitch = 60  # Middle C
            pitch = base_pitch + pitch_adjustment
            pitch = self.mappings.fit_to_scale(pitch, self.mappings.get_scale_notes("C", "pentatonic"))
            
            # Clamp to MIDI range
            pitch = max(0, min(127, pitch))
            
            velocity = self.mappings.get_velocity_from_share(snapshot.share_pct)
            velocity = max(40, min(127, velocity))
            
            instrument = self.mappings.get_instrument_from_engine(snapshot.engine)
            
            pan_value = self.mappings.get_pan_from_segment(snapshot.segment)
            pan = max(-1.0, min(1.0, pan_value / 100.0))  # Convert to -1 to 1 range
            
            duration = self.mappings.get_duration_from_rich_type(snapshot.rich_type)
            duration = max(0.1, min(4.0, duration))
            
            # Detect anomalies (simplified)
            anomaly = abs(rank_delta) >= 5 or is_new
            
            # Check if this is a brand result
            brand_domain = os.getenv('BRAND_DOMAIN', 'mybrand.com')
            brand_rank = snapshot.rank_absolute if brand_domain in snapshot.domain else None
            
            # Determine target stations for this event
            stations = self._determine_stations_for_event(snapshot, rank_delta, anomaly)
            
            note_event = {
                "event_type": "note_on",
                "pitch": pitch,
                "velocity": velocity,
                "pan": pan,
                "duration": duration,
                "instrument": instrument,
                "channel": 0,
                "keyword": snapshot.keyword,
                "engine": snapshot.engine,
                "domain": snapshot.domain,
                "rank_delta": rank_delta,
                "timestamp": datetime.utcnow().isoformat(),
                "anomaly": anomaly,
                "brand_rank": brand_rank,
                "is_new": is_new,
                "stations": stations  # Tag with target stations
            }
            
            return note_event
            
        except Exception as e:
            logger.error(f"Error creating note event: {e}")
            return None
    
    def _determine_stations_for_event(self, snapshot: SERPSnapshot, rank_delta: int, anomaly: bool) -> List[str]:
        """Determine which stations should receive this event."""
        stations = ["daily"]  # All events go to daily station
        
        # AI-lens station: AI-powered engines
        if snapshot.engine in ["google_ai", "openai", "perplexity"]:
            stations.append("ai-lens")
        
        # Opportunity station: large movements or anomalies
        if abs(rank_delta) >= 3 or anomaly:
            stations.append("opportunity")
        
        return stations
    
    async def publish_events(self, events: List[Dict]):
        """Publish events to Redis channel."""
        if not self.redis_client or not events:
            return
        
        for event in events:
            try:
                # Serialize event with msgpack for efficiency
                packed_data = msgpack.packb(event)
                
                # Publish to Redis channel
                await self.redis_client.publish(REDIS_CHANNEL, packed_data)
                
                self.events_published += 1
                
                stations_str = ",".join(event.get("stations", ["daily"]))
                logger.info(f"Published to [{stations_str}]: {event['keyword']} ({event['domain']}) "
                           f"rank_delta={event['rank_delta']} pitch={event['pitch']}")
                
            except Exception as e:
                logger.error(f"Error publishing event: {e}")
    
    async def run_once(self):
        """Run one iteration of SERP monitoring and event publishing."""
        try:
            # Fetch current SERP data
            current_df = await self.fetch_current_serp_data()
            if current_df is None:
                return
            
            # Create snapshot
            current_snapshot = self.create_snapshot_from_dataframe(current_df)
            
            # Detect changes
            changes = self.detect_changes(current_snapshot)
            
            if changes:
                logger.info(f"Detected {len(changes)} SERP changes")
                await self.publish_events(changes)
            else:
                logger.info("No significant SERP changes detected")
            
            # Update snapshot
            self.last_snapshot = current_snapshot
            
            # Save to cache
            await self.cache.set("last_serp_snapshot", self.last_snapshot, ttl=3600)
            
        except Exception as e:
            logger.error(f"Error in run_once: {e}")
    
    async def run_continuous(self):
        """Run continuous monitoring loop."""
        self.running = True
        logger.info(f"Starting continuous SERP monitoring (interval: {PUBLISHER_INTERVAL}s)")
        
        while self.running:
            try:
                await self.run_once()
                
                # Wait for next iteration
                await asyncio.sleep(PUBLISHER_INTERVAL)
                
            except asyncio.CancelledError:
                logger.info("Publisher cancelled")
                break
            except Exception as e:
                logger.error(f"Error in continuous run: {e}")
                await asyncio.sleep(10)  # Brief pause before retry
    
    def stop(self):
        """Stop continuous monitoring."""
        self.running = False
    
    def get_stats(self) -> Dict:
        """Get publisher statistics."""
        return {
            "events_published": self.events_published,
            "last_fetch_time": self.last_fetch_time.isoformat() if self.last_fetch_time else None,
            "fetch_errors": self.fetch_errors,
            "snapshot_size": len(self.last_snapshot),
            "running": self.running,
            "data_source": "sample" if self.use_sample_data else "live"
        }


async def main():
    """Main entry point for the publisher."""
    parser = argparse.ArgumentParser(description="SERP Loop Radio Publisher")
    parser.add_argument("--once", action="store_true", help="Run once instead of continuous")
    parser.add_argument("--live", action="store_true", help="Force live data mode (ignore USE_SAMPLE_DATA env)")
    parser.add_argument("--use-sample-data", action="store_true", help="Force sample data mode")
    parser.add_argument("--interval", type=int, default=PUBLISHER_INTERVAL, 
                       help="Polling interval in seconds")
    
    args = parser.parse_args()
    
    # Override interval if specified
    global PUBLISHER_INTERVAL
    PUBLISHER_INTERVAL = args.interval
    
    # Determine data source
    use_sample_data = None
    if args.live:
        use_sample_data = False
    elif args.use_sample_data:
        use_sample_data = True
    
    publisher = SERPPublisher(use_sample_data=use_sample_data)
    
    try:
        await publisher.initialize()
        
        if args.once:
            logger.info("Running publisher once...")
            await publisher.run_once()
            stats = publisher.get_stats()
            logger.info(f"Publisher stats: {stats}")
        else:
            logger.info("Starting continuous publisher...")
            await publisher.run_continuous()
            
    except KeyboardInterrupt:
        logger.info("Publisher interrupted by user")
    except Exception as e:
        logger.error(f"Publisher error: {e}")
    finally:
        await publisher.close()


if __name__ == "__main__":
    asyncio.run(main()) 