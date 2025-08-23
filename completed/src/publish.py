"""
Publishing module for SERP Loop Radio.
Handles S3 uploads, RSS feed generation, and HTML player creation.
"""

import os
import boto3
import json
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin
import logging

from feedgen.feed import FeedGenerator
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


class SERPPublisher:
    """Main class for publishing audio content and feeds."""
    
    def __init__(self):
        """Initialize publisher with AWS configuration."""
        self.bucket_name = os.getenv("S3_BUCKET", "ti-radio")
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        
        # Initialize S3 client
        try:
            self.s3_client = boto3.client('s3', region_name=self.aws_region)
            logger.info(f"Initialized S3 client for bucket: {self.bucket_name}")
        except NoCredentialsError:
            logger.warning("AWS credentials not found. S3 publishing will be disabled.")
            self.s3_client = None
        
        # Base URLs
        self.base_url = f"https://{self.bucket_name}.s3.{self.aws_region}.amazonaws.com"
    
    def upload_to_s3(
        self, 
        local_path: Path, 
        s3_key: str,
        content_type: str = "audio/mpeg",
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload file to S3 bucket.
        
        Args:
            local_path: Local file path
            s3_key: S3 object key
            content_type: MIME content type
            metadata: Optional metadata dict
            
        Returns:
            Public URL of uploaded file
        """
        if not self.s3_client:
            logger.error("S3 client not available")
            raise RuntimeError("S3 client not configured")
        
        try:
            # Prepare upload arguments
            upload_args = {
                'ContentType': content_type,
                'ACL': 'public-read'  # Make file publicly accessible
            }
            
            if metadata:
                upload_args['Metadata'] = metadata
            
            # Upload file
            logger.info(f"Uploading {local_path} to s3://{self.bucket_name}/{s3_key}")
            
            self.s3_client.upload_file(
                str(local_path),
                self.bucket_name,
                s3_key,
                ExtraArgs=upload_args
            )
            
            # Return public URL
            public_url = f"{self.base_url}/{s3_key}"
            logger.info(f"Successfully uploaded to {public_url}")
            
            return public_url
            
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Upload error: {e}")
            raise
    
    def publish_daily_audio(
        self, 
        mp3_path: Path, 
        report_date: date,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Publish daily audio report to S3.
        
        Args:
            mp3_path: Local MP3 file path
            report_date: Date of the report
            metadata: Optional metadata about the report
            
        Returns:
            Public URL of uploaded MP3
        """
        # Generate S3 key with date structure
        s3_key = f"{report_date.year:04d}/{report_date.month:02d}/{report_date.day:02d}/serp-daily.mp3"
        
        # Prepare metadata
        upload_metadata = {
            'report-date': report_date.isoformat(),
            'generated-at': datetime.utcnow().isoformat(),
            'content-type': 'serp-audio-report'
        }
        
        if metadata:
            upload_metadata.update({k: str(v) for k, v in metadata.items()})
        
        # Upload to S3
        public_url = self.upload_to_s3(
            mp3_path, 
            s3_key, 
            content_type="audio/mpeg",
            metadata=upload_metadata
        )
        
        return public_url
    
    def update_rss_feed(
        self, 
        audio_url: str, 
        report_date: date,
        title: str = None,
        description: str = None,
        duration: Optional[float] = None
    ) -> Path:
        """
        Update RSS feed with new episode.
        
        Args:
            audio_url: Public URL of audio file
            report_date: Date of the report
            title: Episode title (optional)
            description: Episode description (optional)
            duration: Audio duration in seconds (optional)
            
        Returns:
            Path to updated RSS feed file
        """
        # Download existing feed or create new one
        feed_s3_key = "feed.xml"
        local_feed_path = Path("/tmp/feed.xml")
        
        try:
            # Try to download existing feed
            self.s3_client.download_file(
                self.bucket_name, 
                feed_s3_key, 
                str(local_feed_path)
            )
            logger.info("Downloaded existing RSS feed")
        except ClientError:
            logger.info("No existing RSS feed found, creating new one")
        
        # Create/update feed
        fg = self._create_feed_generator()
        
        # Load existing entries if feed exists
        if local_feed_path.exists():
            try:
                # For MVP, we'll recreate the feed each time
                # In production, would parse existing entries
                pass
            except Exception as e:
                logger.warning(f"Could not parse existing feed: {e}")
        
        # Add new episode
        episode_title = title or f"SERP Loop Radio - {report_date.strftime('%Y-%m-%d')}"
        episode_description = description or f"Daily SERP ranking sonification for {report_date}"
        
        fe = fg.add_entry()
        fe.id(audio_url)
        fe.title(episode_title)
        fe.description(episode_description)
        fe.enclosure(audio_url, str(duration or 0), 'audio/mpeg')
        fe.pubDate(datetime.combine(report_date, datetime.min.time()))
        fe.link(audio_url)
        
        # Generate RSS XML
        rss_xml = fg.rss_str(pretty=True)
        
        # Save locally
        with open(local_feed_path, 'wb') as f:
            f.write(rss_xml)
        
        # Upload updated feed
        self.upload_to_s3(
            local_feed_path,
            feed_s3_key,
            content_type="application/rss+xml"
        )
        
        logger.info(f"Updated RSS feed with episode: {episode_title}")
        return local_feed_path
    
    def _create_feed_generator(self) -> FeedGenerator:
        """Create base RSS feed generator."""
        fg = FeedGenerator()
        
        # Feed metadata
        fg.title("SERP Loop Radio")
        fg.description("Daily SERP ranking data converted to musical audio reports")
        fg.link(href=self.base_url, rel='alternate')
        fg.logo(f"{self.base_url}/logo.png")
        fg.subtitle("Data Sonification for SEO Professionals")
        fg.language("en")
        fg.copyright("SERP Loop Radio")
        fg.managingEditor("hello@serploop.radio")
        fg.webMaster("hello@serploop.radio")
        
        # Podcast-specific metadata
        fg.podcast.itunes_category('Technology')
        fg.podcast.itunes_explicit('no')
        fg.podcast.itunes_author('SERP Loop Radio')
        fg.podcast.itunes_summary('Transform your daily SERP data into musical insights')
        
        return fg
    
    def create_html_player(
        self, 
        audio_url: str, 
        report_date: date,
        recent_episodes: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Create HTML player page.
        
        Args:
            audio_url: URL of latest audio file
            report_date: Date of the latest report
            recent_episodes: List of recent episodes
            
        Returns:
            HTML content as string
        """
        recent_episodes = recent_episodes or []
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SERP Loop Radio - {report_date.strftime('%Y-%m-%d')}</title>
    <style>
        body {{
            font-family: 'Arial', sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }}
        .container {{
            background: rgba(255, 255, 255, 0.1);
            padding: 30px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }}
        h1 {{
            text-align: center;
            margin-bottom: 30px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        .player {{
            text-align: center;
            margin: 30px 0;
            padding: 20px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
        }}
        audio {{
            width: 100%;
            max-width: 500px;
        }}
        .date {{
            text-align: center;
            font-size: 1.2em;
            margin-bottom: 20px;
            opacity: 0.9;
        }}
        .recent-episodes {{
            margin-top: 40px;
        }}
        .recent-episodes h3 {{
            border-bottom: 2px solid rgba(255,255,255,0.3);
            padding-bottom: 10px;
        }}
        .episode {{
            padding: 10px;
            margin: 10px 0;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 5px;
        }}
        .episode a {{
            color: #fff;
            text-decoration: none;
        }}
        .episode a:hover {{
            text-decoration: underline;
        }}
        .description {{
            margin: 20px 0;
            line-height: 1.6;
            opacity: 0.9;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 SERP Loop Radio</h1>
        <div class="date">Daily Report - {report_date.strftime('%B %d, %Y')}</div>
        
        <div class="description">
            <p>Experience your SERP ranking data as music. Each search engine, ranking change, 
            and competitive movement is transformed into musical elements using our proprietary 
            FATLD (Frequency, Amplitude, Timbre, Location, Duration) mapping system.</p>
        </div>
        
        <div class="player">
            <audio controls preload="auto">
                <source src="{audio_url}" type="audio/mpeg">
                Your browser does not support the audio element.
            </audio>
            <br><br>
            <a href="{audio_url}" download>📥 Download MP3</a>
        </div>
        
        <div class="recent-episodes">
            <h3>Recent Episodes</h3>
            {"".join([
                f'<div class="episode"><a href="{ep["url"]}">{ep["title"]}</a></div>'
                for ep in recent_episodes[:7]
            ]) if recent_episodes else '<p>No previous episodes available.</p>'}
        </div>
        
        <div style="text-align: center; margin-top: 40px; opacity: 0.7;">
            <p>Generated by SERP Loop Radio | <a href="{self.base_url}/feed.xml" style="color: #fff;">RSS Feed</a></p>
        </div>
    </div>
</body>
</html>
"""
        return html_content
    
    def publish_html_player(
        self, 
        audio_url: str, 
        report_date: date,
        recent_episodes: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Create and publish HTML player page.
        
        Args:
            audio_url: URL of latest audio file
            report_date: Date of the latest report
            recent_episodes: List of recent episodes
            
        Returns:
            Public URL of HTML player
        """
        # Create HTML content
        html_content = self.create_html_player(audio_url, report_date, recent_episodes)
        
        # Save to temporary file
        temp_html = Path("/tmp/index.html")
        with open(temp_html, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Upload to S3
        html_url = self.upload_to_s3(
            temp_html,
            "index.html",
            content_type="text/html"
        )
        
        logger.info(f"Published HTML player: {html_url}")
        return html_url
    
    def publish_complete_report(
        self, 
        mp3_path: Path, 
        report_date: date,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Complete publishing workflow: upload audio, update RSS, create player.
        
        Args:
            mp3_path: Local MP3 file path
            report_date: Date of the report
            metadata: Optional report metadata
            
        Returns:
            Dictionary with URLs of published content
        """
        logger.info(f"Publishing complete report for {report_date}")
        
        results = {}
        
        try:
            # Upload audio file
            audio_url = self.publish_daily_audio(mp3_path, report_date, metadata)
            results['audio_url'] = audio_url
            
            # Update RSS feed
            duration = metadata.get('duration') if metadata else None
            self.update_rss_feed(audio_url, report_date, duration=duration)
            results['rss_url'] = f"{self.base_url}/feed.xml"
            
            # Create and publish HTML player
            html_url = self.publish_html_player(audio_url, report_date)
            results['player_url'] = html_url
            
            logger.info("Successfully published complete report")
            return results
            
        except Exception as e:
            logger.error(f"Publishing failed: {e}")
            # Fail gracefully - log error but don't crash
            return {"error": str(e)}


def publish_mp3_to_s3(
    mp3_path: Path, 
    report_date: date = None,
    metadata: Dict[str, Any] = None
) -> Dict[str, str]:
    """
    Convenience function to publish MP3 with complete workflow.
    
    Args:
        mp3_path: Local MP3 file path
        report_date: Date of the report (defaults to today)
        metadata: Optional metadata
        
    Returns:
        Dictionary with URLs of published content
    """
    if report_date is None:
        report_date = date.today()
    
    publisher = SERPPublisher()
    return publisher.publish_complete_report(mp3_path, report_date, metadata)


if __name__ == "__main__":
    # Test publishing functionality
    publisher = SERPPublisher()
    
    # Test HTML generation
    test_html = publisher.create_html_player(
        "https://example.com/test.mp3",
        date.today(),
        [
            {"title": "Test Episode 1", "url": "https://example.com/ep1.mp3"},
            {"title": "Test Episode 2", "url": "https://example.com/ep2.mp3"}
        ]
    )
    
    print("Generated HTML player:")
    print(test_html[:500] + "...")
    
    # Test with actual file if available
    test_mp3 = Path("/tmp/test_serp.mp3")
    if test_mp3.exists():
        try:
            results = publisher.publish_complete_report(test_mp3, date.today())
            print("Publishing results:", results)
        except Exception as e:
            print(f"Publishing test failed: {e}")
    else:
        print("No test MP3 file found. Run previous modules first.") 