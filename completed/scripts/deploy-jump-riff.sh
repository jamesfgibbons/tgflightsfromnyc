#!/bin/bash

# Deploy Jump Riff - Full 4-bar MIDI playback with dynamic grading
# Replaces simple bass loop with polyphonic Van Halen-style riff

set -e

# Configuration
SERVER="${1:-root@YOUR_SERVER_IP}"  # Replace with your actual server
PROJECT_DIR="/opt/serpradio"
BACKUP_DIR="/opt/serpradio/backups"

echo "🎸 Deploying Jump Riff to $SERVER..."

# Create backup of current configuration
echo "📦 Creating backup..."
ssh $SERVER "
    mkdir -p $BACKUP_DIR/$(date +%Y%m%d_%H%M%S)
    cp -r $PROJECT_DIR/widget/player.js $BACKUP_DIR/$(date +%Y%m%d_%H%M%S)/ || true
    cp -r $PROJECT_DIR/src/note_streamer.py $BACKUP_DIR/$(date +%Y%m%d_%H%M%S)/ || true
    cp -r /etc/nginx/sites-enabled/serpradio $BACKUP_DIR/$(date +%Y%m%d_%H%M%S)/ || true
"

# Create MIDI directory structure
echo "🎵 Setting up MIDI directory..."
ssh $SERVER "
    mkdir -p $PROJECT_DIR/widget/midi
    mkdir -p $PROJECT_DIR/widget/samples
"

# Upload updated files
echo "📤 Uploading updated files..."
scp widget/player.js $SERVER:$PROJECT_DIR/widget/
scp src/note_streamer.py $SERVER:$PROJECT_DIR/src/
scp widget/midi/README.md $SERVER:$PROJECT_DIR/widget/midi/

# Upload MIDI file if it exists
if [ -f "widget/midi/jump_theme.mid" ]; then
    echo "🎹 Uploading Jump theme MIDI..."
    scp widget/midi/jump_theme.mid $SERVER:$PROJECT_DIR/widget/midi/
else
    echo "⚠️  No jump_theme.mid found - you'll need to upload this manually"
fi

# Setup nginx MIDI serving
echo "🌐 Configuring nginx for MIDI serving..."
scp infra/nginx/serpradio_midi.conf $SERVER:/etc/nginx/snippets/

ssh $SERVER "
    # Add MIDI config to main site if not already present
    if ! grep -q 'serpradio_midi.conf' /etc/nginx/sites-enabled/serpradio; then
        sed -i '/server_name/a \    include snippets/serpradio_midi.conf;' /etc/nginx/sites-enabled/serpradio
        echo '✅ Added MIDI config to nginx'
    else
        echo '✅ MIDI config already present in nginx'
    fi

    # Test nginx configuration
    nginx -t
    if [ \$? -eq 0 ]; then
        echo '✅ Nginx configuration valid'
        systemctl reload nginx
        echo '✅ Nginx reloaded'
    else
        echo '❌ Nginx configuration error - deployment stopped'
        exit 1
    fi
"

# Rebuild and restart the application
echo "🔄 Rebuilding application..."
ssh $SERVER "
    cd $PROJECT_DIR
    
    # Stop the current service
    docker compose -f docker-compose.prod.yml down
    
    # Rebuild with new code
    docker compose -f docker-compose.prod.yml up -d --build api
    
    # Wait for service to start
    sleep 8
    
    # Health check
    if curl -f https://api.serpradio.com/health > /dev/null 2>&1; then
        echo '✅ API health check passed'
    else
        echo '❌ API health check failed'
        exit 1
    fi
"

# Test MIDI serving
echo "🎹 Testing MIDI file serving..."
ssh $SERVER "
    if [ -f $PROJECT_DIR/widget/midi/jump_theme.mid ]; then
        if curl -f -I https://api.serpradio.com/midi/jump_theme.mid > /dev/null 2>&1; then
            echo '✅ MIDI file serving works'
        else
            echo '⚠️  MIDI file serving may have issues - check nginx logs'
        fi
    else
        echo '⚠️  No MIDI file to test - upload jump_theme.mid manually'
    fi
"

echo ""
echo "🎸 Jump Riff deployment complete!"
echo ""
echo "Next steps:"
echo "1. Upload a 4-bar jump_theme.mid file to widget/midi/ if you haven't already"
echo "2. Test with your CSV files using 'Play Time Series'"
echo "3. Listen for the full riff instead of simple bass notes"
echo ""
echo "Features deployed:"
echo "✅ MIDI-based polyphonic riff playback"
echo "✅ Dynamic transpose based on average rank"
echo "✅ Tempo changes based on click deltas"
echo "✅ Velocity modulation based on top-3 keyword gains"
echo "✅ CTR jump detection with guitar fill overlays"
echo "✅ Nginx MIDI file serving with proper MIME types"
echo ""
echo "The widget now sounds like a mini-studio mix! 🎵" 