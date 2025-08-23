# 🚀 SERP Loop Radio Live - Quick Start Checklist

Get SERP Loop Radio's live streaming system working in **5 minutes**!

## ✅ Prerequisites Check

- [ ] **Docker & Docker Compose** installed
- [ ] **Node.js 18+** installed
- [ ] **Git** installed

## 🔧 Setup Steps

### 1. Environment Configuration (2 minutes)

```bash
# Copy environment template
cp env.template .env

# Add these basic settings for testing:
echo "USE_SAMPLE_DATA=true" >> .env
echo "LIVE_MODE_TOKEN=dev-token-123" >> .env
echo "REDIS_URL=redis://localhost:6379" >> .env
echo "BRAND_DOMAIN=mybrand.com" >> .env
```

### 2. Install Dependencies (1 minute)

```bash
# Install frontend dependencies
make live-setup
```

### 3. Start Live System (1 minute)

```bash
# Start all services (Redis, API, Publisher, React UI)
make live-dev
```

**Wait for all services to start** - you'll see logs from Redis, API, and React dev server.

### 4. Test with Sample Data (1 minute)

```bash
# In a NEW terminal window, start the test publisher
make test-publisher
```

This will simulate SERP ranking changes using the sample data.

### 5. Open the Live Interface

Open your browser to: **http://localhost:5173**

1. Click **"🔊 Start Audio"** button
2. Select a station (Daily, AI Lens, or Opportunity)  
3. **Listen** to your SERP data being converted to music in real-time!

## 🎵 What You Should See/Hear

- **Connection Status**: Green "● Connected" in top right
- **Recent Events**: Live SERP events appearing in the bottom section
- **Audio**: Musical notes playing as events stream in
- **Visual Feedback**: Screen flashes red for anomalies

## 🧪 Testing Different Modes

```bash
# Test all stations with specific events
make test-stations

# Publish all sample data at once
make test-publisher-batch

# Stream with random changes
make test-publisher --simulate-changes
```

## 🌐 For Your Lovable Domain

### Frontend Only (Easiest)

1. **Build the React app**:
   ```bash
   cd ui
   npm run build
   ```

2. **Upload `ui/dist/` folder** to your Lovable hosting

3. **Configure environment** in Lovable dashboard:
   ```
   VITE_WS_URL=wss://your-api-server.com/ws/serp
   VITE_API_KEY=your-production-token
   ```

### Full Stack (Advanced)

- Deploy the Docker Compose setup to a VPS/cloud server
- Point your Lovable domain to the React frontend
- Configure backend separately

## 🆘 If Something Goes Wrong

### Common Issues:

1. **"Docker not found"** → Install Docker Desktop
2. **"Port 5173 already in use"** → Kill process: `lsof -ti:5173 | xargs kill`
3. **"No audio events"** → Make sure test publisher is running: `make test-publisher`
4. **"Connection failed"** → Wait for all services to start, check Docker logs

### Quick Fixes:

```bash
# Stop everything
make live-stop

# Clean restart
docker system prune -f
make live-dev

# Check service health
curl http://localhost:8000/health
```

### Get Help:

```bash
# View all available commands
make help

# Test WebSocket functionality
make test-websocket

# View service logs
make live-logs
```

## 🎯 Next Steps

Once you have it working locally:

1. **Customize the audio** by editing `config/mapping.json`
2. **Add your SERP data** by configuring DataForSEO API credentials
3. **Deploy to production** using the `DEPLOYMENT.md` guide
4. **Experiment with stations** and musical parameters

---

**🎉 You're now listening to your SERP data live!** 

Need more help? Check `README.md` for full documentation or `DEPLOYMENT.md` for production setup. 