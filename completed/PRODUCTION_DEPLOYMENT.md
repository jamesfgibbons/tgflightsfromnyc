# SERP Radio Production Deployment Guide

## 🎵 Enhanced Proof-of-Concept Ready for Production

This deployment guide covers the enhanced SERP Radio with professional audio quality, secure embedding, and MIDI export capabilities.

## Sound Quality Enhancements ✅

### Implemented Improvements:
- ✅ **Master Limiter**: Prevents clipping at -1dB threshold
- ✅ **Warmer Bass**: MembraneSynth for punchy Van Halen "Jump" loop
- ✅ **Overlay Samples**: Set to -6dB to avoid masking the motif
- ✅ **Humanized Timing**: ±20ms swing for musical feel
- ✅ **Improved Filter Glide**: 1-second breathe-down for AI steal effects

### Audio Routing:
```
All Synths → Filter (AI effects) → Master Limiter → Destination
Bass Synth → Master Limiter → Destination
Overlay Samples → Master Limiter → Destination (-6dB)
```

## Production Backend Features ✅

### Memory Protection:
- CSV files limited to 50,000 rows (auto-sampling with deterministic seed)
- In-memory session store with automatic cleanup
- Domain extraction from URLs for proper brand hit detection

### Enhanced CSV Support:
- **GSC Format**: `date`, `query`/`page`, `clicks`, `impressions`, `position`
- **Rank File**: `keyword`, `url`, `position`, `search_volume`
- Auto-detection based on column headers
- Comprehensive validation and error handling

### MIDI Export:
- Endpoint: `GET /download/midi?session=SESSION_ID&mode=time`
- Standard MIDI format with proper note timing
- Automatic cleanup of temporary files
- Client-side download trigger after playback completion

## Deployment Steps

### 1. Server Setup
```bash
# Build production Docker image
docker build -f docker/Dockerfile.prod -t serpradio:latest .

# Run with environment variables
docker run -d \
  --name serpradio \
  -p 8000:8000 \
  -e CLIENT_DOMAIN=your-domain.com \
  -e USE_SAMPLE_DATA=false \
  -v /tmp/midi:/tmp/midi \
  serpradio:latest
```

### 2. Nginx SSL Configuration
Copy `infra/nginx-serpradio-ssl.conf` to your nginx sites-enabled:
```bash
sudo cp infra/nginx-serpradio-ssl.conf /etc/nginx/sites-available/serpradio
sudo ln -s /etc/nginx/sites-available/serpradio /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 3. SSL Certificate Setup
```bash
# Using certbot for Let's Encrypt
sudo certbot --nginx -d api.serpradio.com
```

### 4. Environment Configuration
Create `.env.production`:
```env
CLIENT_DOMAIN=your-domain.com
USE_SAMPLE_DATA=false
REDIS_URL=redis://localhost:6379
DATAFORSEO_LOGIN=your_login
DATAFORSEO_PASSWORD=your_password
ALLOWED_ORIGINS=https://api.serpradio.com,https://lovable.dev
MAX_UPLOAD_SIZE=50MB
```

## Security Features ✅

### Content Security Policy:
- `frame-ancestors`: Controls where iframe can be embedded
- `connect-src`: Allows WSS connections to API domain
- `script-src`: Permits Tone.js from unpkg.com

### Iframe Sandbox:
- `allow-scripts`: JavaScript execution
- `allow-same-origin`: Required for WebSocket connections
- `allow-forms`: File upload functionality
- `allow-downloads`: MIDI file downloads

### Headers:
- X-Frame-Options: SAMEORIGIN
- Referrer-Policy: strict-origin-when-cross-origin
- X-Content-Type-Options: nosniff

## Embedding Instructions

### For Lovable or Any Website:
Copy the snippet from `cms/lovable-snippets/serpradio-embed.html`:

```html
<div class="serpradio-container" style="width: 100%; max-width: 760px; margin: 0 auto;">
    <iframe
        src="https://api.serpradio.com/widget/"
        sandbox="allow-scripts allow-same-origin allow-forms allow-downloads"
        referrerpolicy="strict-origin-when-cross-origin"
        style="border:none;width:100%;height:600px;border-radius:12px;"
        title="SERP Radio - CSV Data Sonification">
    </iframe>
</div>
```

## Testing Checklist ✅

### Upload & Playback Test:
1. **Navigate to**: `https://api.serpradio.com/widget/`
2. **Upload**: 100+ row CSV file
3. **Verify**: Progress bar reaches 100%
4. **Listen**: Van Halen Jump bass loop starts
5. **Observe**: Humanized timing, no audio clipping
6. **Check**: Console shows ≤8 WebSocket messages/second

### Audio Quality Test:
1. **Bass**: Should sound warm and punchy (MembraneSynth)
2. **Overlays**: Video/shopping/cash samples audible but not overpowering
3. **Filter**: AI steal effects sweep up and breathe down smoothly
4. **Timing**: Notes feel musical, not robotic

### MIDI Export Test:
1. **After playback**: "Download MIDI 🎹" button appears
2. **Click download**: Generates `.mid` file
3. **Verify**: File is valid MIDI format
4. **Open**: In DAW/music software to confirm notes

### Iframe Security Test:
1. **Embed**: On test page using provided snippet
2. **Chrome DevTools**: Check for WSS connections (no mixed content warnings)
3. **Network**: Verify all requests use HTTPS/WSS
4. **Console**: No CSP violations

### Production Load Test:
1. **Upload**: Multiple large CSV files simultaneously
2. **Monitor**: Memory usage stays reasonable (<2GB)
3. **Check**: Both uvicorn workers respond
4. **Verify**: Sessions expire after 10 minutes

## Monitoring & Maintenance

### Health Endpoint:
```bash
curl https://api.serpradio.com/health
```
Should return server status, active sessions, and uptime.

### Log Monitoring:
```bash
docker logs -f serpradio
```
Watch for CSV processing, WebSocket connections, and MIDI generation.

### Cleanup MIDI Files:
```bash
# Add to crontab to clean old MIDI files
0 2 * * * find /tmp/midi -name "*.mid" -mtime +1 -delete
```

## Troubleshooting Guide

| Issue | Solution |
|-------|----------|
| "AudioContext not allowed" | Ensure user clicks before `Tone.start()` |
| MIDI export empty | Check `/tmp/midi` permissions |
| Iframe won't load | Verify CSP `frame-ancestors` header |
| Notes off-key | Set `CLIENT_DOMAIN` to match CSV domain data |
| WebSocket fails | Check nginx WSS proxy configuration |
| Upload too large | Adjust `client_max_body_size` in nginx |

## Performance Metrics

### Expected Performance:
- **CSV Processing**: <2 seconds for 50k rows
- **Memory Usage**: <500MB per session
- **Audio Latency**: <50ms note triggering
- **WebSocket Rate**: 4-8 messages/second during playback
- **MIDI Generation**: <1 second for 100 notes

## Final Status: ✅ PRODUCTION READY

The SERP Radio proof-of-concept now includes:
- ✅ Professional audio quality with master limiting
- ✅ Secure iframe embedding with CSP
- ✅ MIDI export functionality
- ✅ Memory-protected CSV processing
- ✅ Production Docker configuration
- ✅ SSL nginx setup
- ✅ Comprehensive testing checklist

**The system is ready for deployment and secure embedding on Lovable or any website.** 