# 🚨 Debug 502 Error on https://api.serpradio.com/

## Problem: 502 Bad Gateway on main API

A 502 error means nginx can't reach the FastAPI backend. The SERP Radio API server is likely not running.

## Step-by-Step Debugging:

### 1. Check if SERP Radio API is running
```bash
ssh root@your-server

# Check if the API process is running
ps aux | grep python | grep api
# Should show: python -m src.api or uvicorn process

# Check if port 8000 is listening
netstat -tlnp | grep :8000
# Should show: tcp 0.0.0.0:8000 LISTEN

# Check Docker containers (if using Docker)
docker ps | grep serpradio
# Should show running container
```

### 2. Check nginx configuration
```bash
# Test nginx config
nginx -t

# Check nginx site config
cat /etc/nginx/sites-enabled/serpradio

# Check if proxy_pass points to correct backend
grep -n "proxy_pass" /etc/nginx/sites-enabled/serpradio
# Should show: proxy_pass http://127.0.0.1:8000;
```

### 3. Check nginx error logs
```bash
tail -f /var/log/nginx/error.log
# Then try accessing https://api.serpradio.com/ in browser
# Look for "connection refused" or "upstream" errors
```

### 4. Check API application logs
```bash
# If running with systemd
journalctl -u serpradio -f

# If running in Docker
docker logs -f serpradio

# If running manually, check where logs are written
```

## Quick Fixes:

### Fix 1: Start the SERP Radio API
```bash
# If using Docker:
cd /opt/serpradio
docker-compose up -d

# If running manually:
cd /opt/serpradio
python -m src.api &

# If using systemd:
systemctl start serpradio
systemctl enable serpradio
```

### Fix 2: Check environment variables
```bash
# Ensure required environment variables are set
echo $CLIENT_DOMAIN
echo $USE_SAMPLE_DATA

# Or check if .env file exists
ls -la /opt/serpradio/.env*
```

### Fix 3: Verify nginx backend configuration
```bash
# Check current nginx config
cat /etc/nginx/sites-enabled/serpradio

# The config should have this location block:
# location / {
#     proxy_pass http://127.0.0.1:8000;
#     proxy_set_header Host $host;
#     proxy_set_header X-Real-IP $remote_addr;
#     proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
#     proxy_set_header X-Forwarded-Proto $scheme;
# }
```

### Fix 4: Manual API startup (for testing)
```bash
# Navigate to SERP Radio directory
cd /opt/serpradio

# Install dependencies if needed
pip install -r requirements.txt
pip install python-multipart aiohttp redis

# Start API manually for testing
python -m src.api

# Check if it starts without errors
# Should show: "Uvicorn running on http://0.0.0.0:8000"
```

## Verification Commands:

### Test API directly on server:
```bash
# Test health endpoint locally on server
curl http://localhost:8000/health

# Should return JSON with "status": "ok"
```

### Test through nginx:
```bash
# Test through nginx (should work after fix)
curl -I https://api.serpradio.com/health

# Should return HTTP/2 200
```

## Complete Startup Script:

Create this script to ensure everything starts correctly:

```bash
#!/bin/bash
# /opt/serpradio/start-api.sh

set -e
cd /opt/serpradio

echo "🚀 Starting SERP Radio API..."

# Set environment variables
export USE_SAMPLE_DATA=false
export CLIENT_DOMAIN=example.com

# Start the API
echo "🔧 Starting FastAPI server..."
python -m src.api &

# Wait for startup
sleep 3

# Test if running
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ API is running on port 8000"
else
    echo "❌ API failed to start"
    exit 1
fi

echo "🌐 API should now be accessible at https://api.serpradio.com/"
```

Make it executable and run:
```bash
chmod +x /opt/serpradio/start-api.sh
/opt/serpradio/start-api.sh
```

## Systemd Service (Recommended):

Create a proper systemd service:

```bash
# Create service file
cat > /etc/systemd/system/serpradio.service << 'EOF'
[Unit]
Description=SERP Radio API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/serpradio
Environment=USE_SAMPLE_DATA=false
Environment=CLIENT_DOMAIN=example.com
ExecStart=/usr/bin/python -m src.api
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable serpradio
systemctl start serpradio

# Check status
systemctl status serpradio
```

## Expected Results After Fix:

✅ `curl http://localhost:8000/health` returns JSON  
✅ `curl -I https://api.serpradio.com/health` returns HTTP/2 200  
✅ `https://api.serpradio.com/` shows the main app HTML  
✅ `https://api.serpradio.com/widget/` loads the widget  

The main issue is likely that the FastAPI backend isn't running. Start with checking if the process is running and start it if needed! 