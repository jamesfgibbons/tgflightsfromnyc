"""
Command-line interface for SERP Loop Radio.
Provides Typer-based commands for data collection, processing, and publishing.
"""

import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
import logging

import typer
from dotenv import load_dotenv
import pandas as pd

# Import our modules
from .fetch_data import collect_serp_data
from .preprocess import preprocess_serp_data, save_processed_data
from .sonify import csv_to_midi
from .render_audio import AudioRenderer
from .publish import publish_mp3_to_s3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Typer app
app = typer.Typer(
    name="serp-loop-radio",
    help="SERP Loop Radio - Convert SERP data to musical audio reports"
)


@app.command()
def run_daily(
    target_date: Optional[str] = typer.Option(
        None, 
        "--date", 
        help="Target date (YYYY-MM-DD). Defaults to today."
    ),
    keywords_file: Path = typer.Option(
        Path("config/keywords.txt"),
        "--keywords",
        help="Path to keywords file"
    ),
    config_file: Path = typer.Option(
        Path("config/mapping.json"),
        "--config",
        help="Path to mapping configuration"
    ),
    output_dir: Path = typer.Option(
        Path("/tmp"),
        "--output",
        help="Output directory for generated files"
    ),
    publish: bool = typer.Option(
        True,
        "--publish/--no-publish",
        help="Whether to publish to S3"
    )
):
    """Run daily SERP collection and audio generation."""
    load_dotenv()
    
    # Parse target date
    if target_date:
        try:
            target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            typer.echo(f"Invalid date format: {target_date}. Use YYYY-MM-DD.")
            raise typer.Exit(1)
    else:
        target_date = date.today()
    
    typer.echo(f"🎵 Running SERP Loop Radio for {target_date}")
    
    try:
        # Step 1: Collect SERP data
        typer.echo("📊 Collecting SERP data...")
        df = collect_serp_data(target_date, keywords_file)
        
        if df.empty:
            typer.echo("❌ No SERP data collected. Check API credentials and keywords.")
            raise typer.Exit(1)
        
        typer.echo(f"✅ Collected {len(df)} SERP records")
        
        # Step 2: Preprocess data
        typer.echo("🔄 Preprocessing data...")
        
        # Look for previous day's data
        prev_csv_path = output_dir / f"serp_data_{(target_date - timedelta(days=1)).isoformat()}.csv"
        
        df_processed = preprocess_serp_data(df, prev_csv_path)
        
        # Save processed data
        csv_output_path = output_dir / f"serp_data_{target_date.isoformat()}.csv"
        save_processed_data(df_processed, csv_output_path)
        
        typer.echo(f"✅ Preprocessed and saved data to {csv_output_path}")
        
        # Step 3: Convert to MIDI
        typer.echo("🎼 Converting to MIDI...")
        
        midi_path = csv_to_midi(df_processed, config_file)
        typer.echo(f"✅ Created MIDI file: {midi_path}")
        
        # Step 4: Render audio
        typer.echo("🔊 Rendering audio...")
        
        renderer = AudioRenderer(config_file)
        mp3_path = output_dir / f"serp_audio_{target_date.isoformat()}.mp3"
        
        renderer.midi_to_mp3(midi_path, mp3_path)
        typer.echo(f"✅ Created MP3 file: {mp3_path}")
        
        # Step 5: Publish if requested
        if publish:
            typer.echo("🚀 Publishing to S3...")
            
            # Get audio duration for metadata
            audio_info = renderer.get_audio_info(mp3_path)
            metadata = {
                "duration": audio_info.get("duration", 0),
                "records_count": len(df_processed),
                "anomalies_count": df_processed.get("anomaly", pd.Series(False)).sum()
            }
            
            results = publish_mp3_to_s3(mp3_path, target_date, metadata)
            
            if "error" in results:
                typer.echo(f"❌ Publishing failed: {results['error']}")
            else:
                typer.echo("✅ Successfully published:")
                typer.echo(f"   🎵 Audio: {results.get('audio_url')}")
                typer.echo(f"   📻 RSS: {results.get('rss_url')}")
                typer.echo(f"   🌐 Player: {results.get('player_url')}")
        
        typer.echo(f"🎉 Daily report complete for {target_date}")
        
    except Exception as e:
        logger.error(f"Daily run failed: {e}")
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1)


@app.command()
def run_weekly(
    start_date: Optional[str] = typer.Option(
        None,
        "--start",
        help="Start date (YYYY-MM-DD). Defaults to 7 days ago."
    ),
    end_date: Optional[str] = typer.Option(
        None,
        "--end", 
        help="End date (YYYY-MM-DD). Defaults to today."
    )
):
    """Run weekly batch processing for multiple days."""
    load_dotenv()
    
    # Parse dates
    if end_date:
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end_date = date.today()
    
    if start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    else:
        start_date = end_date - timedelta(days=6)  # 7 days total
    
    typer.echo(f"📅 Running weekly batch from {start_date} to {end_date}")
    
    current_date = start_date
    while current_date <= end_date:
        typer.echo(f"\n📍 Processing {current_date}")
        
        # Run daily for this date
        try:
            app.commands["run-daily"].callback(
                target_date=current_date.isoformat(),
                keywords_file=Path("config/keywords.txt"),
                config_file=Path("config/mapping.json"),
                output_dir=Path("/tmp"),
                publish=True
            )
        except Exception as e:
            typer.echo(f"❌ Failed for {current_date}: {e}")
        
        current_date += timedelta(days=1)
    
    typer.echo("✅ Weekly batch complete")


@app.command()
def local_preview(
    csv_file: Path = typer.Argument(..., help="CSV file to sonify"),
    config_file: Path = typer.Option(
        Path("config/mapping.json"),
        "--config",
        help="Path to mapping configuration"
    ),
    play: bool = typer.Option(
        False,
        "--play",
        help="Attempt to play the audio after generation"
    )
):
    """Create audio preview from existing CSV file."""
    load_dotenv()
    
    if not csv_file.exists():
        typer.echo(f"❌ CSV file not found: {csv_file}")
        raise typer.Exit(1)
    
    typer.echo(f"🎵 Creating preview from {csv_file}")
    
    try:
        # Load CSV
        df = pd.read_csv(csv_file)
        typer.echo(f"📊 Loaded {len(df)} records")
        
        # Convert to MIDI
        midi_path = csv_to_midi(df, config_file)
        typer.echo(f"🎼 Created MIDI: {midi_path}")
        
        # Render audio
        renderer = AudioRenderer(config_file)
        mp3_path = Path("/tmp/preview.mp3")
        
        renderer.midi_to_mp3(midi_path, mp3_path)
        typer.echo(f"🔊 Created audio: {mp3_path}")
        
        # Play if requested
        if play:
            import subprocess
            import platform
            
            system = platform.system()
            if system == "Darwin":  # macOS
                subprocess.run(["open", str(mp3_path)])
            elif system == "Linux":
                subprocess.run(["xdg-open", str(mp3_path)])
            elif system == "Windows":
                os.startfile(str(mp3_path))
            else:
                typer.echo("🎵 Audio file created. Open manually to play.")
        
    except Exception as e:
        typer.echo(f"❌ Preview failed: {e}")
        raise typer.Exit(1)


@app.command()
def rebuild_feed(
    audio_dir: Path = typer.Option(
        Path("/tmp"),
        "--audio-dir",
        help="Directory containing audio files"
    ),
    days: int = typer.Option(
        30,
        "--days",
        help="Number of recent days to include"
    )
):
    """Rebuild RSS feed from existing audio files."""
    load_dotenv()
    
    typer.echo(f"📻 Rebuilding RSS feed from {audio_dir}")
    
    # This would scan for existing audio files and rebuild the feed
    # Implementation depends on file naming convention
    typer.echo("🚧 Feed rebuild not yet implemented in MVP")


@app.command()
def call_dataforseo_status():
    """Check DataForSEO API status and account information."""
    load_dotenv()
    
    from .fetch_data import DataForSEOClient
    
    login = os.getenv("DATAFORSEO_LOGIN")
    password = os.getenv("DATAFORSEO_PASSWORD")
    
    if not login or not password:
        typer.echo("❌ DataForSEO credentials not found in environment")
        raise typer.Exit(1)
    
    try:
        client = DataForSEOClient(login, password)
        
        # Make a simple status request
        response = client._make_request("appendix/user_data", [{}])
        
        if response.get("status_code") == 20000:
            tasks = response.get("tasks", [{}])
            if tasks:
                result = tasks[0].get("result", {})
                typer.echo("✅ DataForSEO API Status: OK")
                typer.echo(f"   💰 Balance: ${result.get('money', {}).get('balance', 0)}")
                typer.echo(f"   📊 Limits: {result.get('limits', {})}")
            else:
                typer.echo("✅ API connection successful")
        else:
            typer.echo(f"❌ API Error: {response.get('status_message')}")
            
    except Exception as e:
        typer.echo(f"❌ API check failed: {e}")
        raise typer.Exit(1)


@app.command()
def sample():
    """Generate sample audio from built-in test data."""
    load_dotenv()
    
    typer.echo("🎵 Generating sample audio...")
    
    try:
        from .sonify import SERPSonifier
        
        sonifier = SERPSonifier(Path("config/mapping.json"))
        
        # Create sample MIDI
        midi_path = Path("/tmp/sample.mid")
        sonifier.create_sample_midi(midi_path)
        
        # Render to MP3
        renderer = AudioRenderer(Path("config/mapping.json"))
        mp3_path = Path("/tmp/sample.mp3")
        
        renderer.midi_to_mp3(midi_path, mp3_path)
        
        typer.echo(f"✅ Sample audio created: {mp3_path}")
        typer.echo("🎧 You can now play this file to hear how SERP data sounds!")
        
    except Exception as e:
        typer.echo(f"❌ Sample generation failed: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app() 