# 🚀 SERP Loop Radio Deployment Guide

This guide covers deployment options for SERP Loop Radio, from local development to production deployment.

## 🏃‍♂️ Quick Start (Local Development)

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for UI development)
- Python 3.11+ (for API development)

### 1. Environment Setup

```bash
# Copy environment template
cp env.template .env

# Edit .env with your credentials
# For development, you can use sample data mode:
echo "USE_SAMPLE_DATA=true" >> .env
echo "LIVE_MODE_TOKEN=dev-token-123" >> .env
echo "REDIS_URL=redis://localhost:6379" >> .env
```

### 2. Start Live System

```bash
# Install frontend dependencies
make live-setup

# Start all services (Redis, API, Publisher, React UI)
make live-dev

# Open browser to http://localhost:5173
```

### 3. Test with Sample Data

```bash
# In another terminal, start test publisher
make test-publisher

# Or test specific stations
make test-stations

# Or publish all sample data at once
make test-publisher-batch
```

## 🌍 Production Deployment Options

### Option 1: Docker Compose (Recommended)

For hosting on VPS, cloud instances, or container platforms:

```bash
# 1. Clone repository on server
git clone [your-repo] serp-loop-radio
cd serp-loop-radio

# 2. Configure production environment
cp env.template .env
# Edit .env with production credentials

# 3. Build and start production services
docker-compose -f docker/docker-compose.yml up -d --build

# 4. Setup reverse proxy (nginx/caddy) to point to:
# - Frontend: localhost:5173
# - API: localhost:8000
```

#### Nginx Reverse Proxy Setup

Create `/etc/nginx/sites-available/serp-loop-radio`:

```nginx
server {
    server_name your-domain.com;
    
    # Frontend (React app)
    location / {
        proxy_pass http://localhost:5173;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
    
    # API endpoints
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket endpoint
    location /ws/ {
        proxy_pass http://localhost:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

Enable the site and install SSL:

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/serp-loop-radio /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Install SSL with Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

#### Complete Ubuntu Server Setup (15-minute runbook)

```bash
#!/bin/bash
# SERP Loop Radio - Ubuntu Server Setup

# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 3. Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 4. Install Nginx
sudo apt install nginx -y

# 5. Clone repository
git clone https://github.com/your-username/serp-loop-radio.git
cd serp-loop-radio

# 6. Configure environment
cp env.template .env
echo "Edit .env with your credentials:"
echo "  DATAFORSEO_LOGIN=your_login"
echo "  DATAFORSEO_PASSWORD=your_password"
echo "  LIVE_MODE_TOKEN=$(openssl rand -hex 32)"
echo "  REDIS_URL=redis://redis:6379"
nano .env

# 7. Start services
docker-compose -f docker/docker-compose.yml up -d

# 8. Setup Nginx (follow steps above)

# 9. Install SSL
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com

echo "🎉 SERP Loop Radio deployed successfully!"
echo "Visit https://your-domain.com to see the live interface"
```

### Option 2: Lovable Hosted Domain

If using Lovable's hosting platform:

#### Frontend (React App)

```bash
# 1. Build React app for production
cd ui
npm run build

# 2. Deploy dist/ folder to Lovable hosting
# - Upload contents of ui/dist/ to your domain
# - Configure build command: npm run build
# - Configure output directory: dist
```

#### Backend (API + Publisher)

```bash
# Option A: Deploy as containerized service
# - Use docker/docker-compose.yml
# - Configure environment variables in Lovable dashboard

# Option B: Deploy Python components separately
# - Deploy FastAPI server (src/live_server.py) 
# - Deploy Redis instance
# - Deploy publisher (src/publisher.py or src/test_publisher.py)
```

### Option 3: Serverless Deployment

For AWS Lambda or similar platforms:

```bash
# Package backend for serverless
zip -r serp-loop-radio.zip src/ requirements.txt

# Deploy using your serverless framework of choice
# Note: WebSocket support may require API Gateway configuration
```

## 🔧 Configuration for Production

### Environment Variables

```bash
# Production API credentials
DATAFORSEO_LOGIN=your_production_login
DATAFORSEO_PASSWORD=your_production_password

# AWS for file storage
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
S3_BUCKET=your-production-bucket

# Redis (use managed Redis service in production)
REDIS_URL=redis://your-redis-host:6379

# Security
LIVE_MODE_TOKEN=your-secure-production-token

# Performance
PUBLISHER_INTERVAL=90  # seconds between SERP checks
```

### Frontend Environment (ui/.env.production)

```bash
VITE_WS_URL=wss://your-domain.com/ws/serp
VITE_API_KEY=your-secure-production-token
```

### Security Considerations

1. **Use HTTPS/WSS in production**
2. **Secure Redis with authentication**
3. **Use strong API tokens**
4. **Configure CORS properly**
5. **Rate limit WebSocket connections**

## 🎯 Lovable-Specific Deployment

### Frontend Deployment

1. **Build Settings**:
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Root Directory: `ui`

2. **Environment Variables** (in Lovable dashboard):
   ```
   VITE_WS_URL=wss://your-api-domain.com/ws/serp
   VITE_API_KEY=your-production-token
   ```

### Backend Options for Lovable

#### Option A: External Backend
- Host API/Redis on separate service (DigitalOcean, AWS, etc.)
- Point frontend to external WebSocket endpoint

#### Option B: Lovable Full-Stack (if supported)
- Deploy entire Docker Compose setup
- Configure internal networking between services

### Recommended Architecture

```
[Lovable Frontend] → [External API + Redis] → [SERP Data Sources]
    (React UI)         (VPS/Cloud Server)       (DataForSEO API)
```

## 📊 Monitoring & Maintenance

### Health Checks

```bash
# API health
curl https://your-domain.com/health

# WebSocket connection test
# Use browser developer tools to test WebSocket connection

# Redis status
redis-cli ping
```

### Logs

```bash
# Docker Compose logs
docker-compose logs -f

# Individual service logs
docker-compose logs live-api
docker-compose logs publisher
```

### Scaling

- **Frontend**: Static files, scales automatically
- **API**: Scale horizontally behind load balancer
- **Redis**: Use managed Redis service for reliability
- **Publisher**: Single instance sufficient for most use cases

## 🚨 Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
   - Check CORS configuration
   - Verify WSS vs WS protocol
   - Check firewall/proxy settings

2. **No Audio Events**
   - Verify publisher is running
   - Check Redis connection
   - Verify sample data exists

3. **Frontend Build Issues**
   - Clear node_modules and reinstall
   - Check Node.js version compatibility
   - Verify environment variables

### Support Commands

```bash
# Test WebSocket functionality
make test-websocket

# Test complete live system
make live-test

# View all available commands
make help
```

---

**Need Help?** Check the main README.md for additional documentation and troubleshooting tips.

# 🚀 **Phase 2.5 - Production Ready**

This guide covers deploying SERP Loop Radio with **WSS (WebSocket Secure)** support, which is required for production use when frontend is served over HTTPS.

---

## **Quick Production Setup (15 minutes)**

### **Option 1: Render.com (Recommended for MVP)**

1. **Backend Deployment**:
   ```bash
   # Fork/push this repo to GitHub
   git add . && git commit -m "Phase 2.5 ready" && git push
   
   # On Render.com:
   # - Create new "Web Service" 
   # - Connect GitHub repo
   # - Build Command: `cd backend && pip install -r requirements.txt`
   # - Start Command: `cd src && python live_server.py`
   # - Environment: Add DataForSEO credentials
   ```

2. **Redis Setup**:
   ```bash
   # On Render.com:
   # - Create new "Redis" service
   # - Copy internal Redis URL to web service environment
   ```

3. **Frontend (Lovable)**:
   ```bash
   # Build React app locally
   cd ui && npm run build
   
   # Upload dist/ folder to Lovable hosting
   # Set environment variable:
   # VITE_WS_URL=wss://your-api.onrender.com/ws/serp
   ```

### **Option 2: Ubuntu Server with SSL (30 minutes)**

Complete production setup with custom domain and SSL certificates:

#### **🚀 Automated Deployment (Recommended)**

Use the automated deployment script for serpradio.com:

```bash
# 1. Upload the deployment script to your server
scp infra/scripts/deploy-serpradio.sh root@159.223.153.111:/tmp/

# 2. Run the automated deployment
ssh root@159.223.153.111 "chmod +x /tmp/deploy-serpradio.sh && /tmp/deploy-serpradio.sh"

# 3. Edit credentials (when prompted)
ssh root@159.223.153.111 "nano /opt/serpradio/.env.production"

# 4. Deploy frontend
make build-frontend
make deploy-frontend-rsync SERVER=159.223.153.111 USER=root

# 5. Restart services with new credentials
ssh root@159.223.153.111 "cd /opt/serpradio && docker compose -f docker/docker-compose.yml restart"
```

The automated script handles:
- ✅ System updates and package installation
- ✅ Docker and nginx setup
- ✅ SSL certificate generation with Let's Encrypt
- ✅ Firewall and security configuration
- ✅ Health monitoring setup
- ✅ Log rotation and automatic updates
- ✅ Complete validation testing

#### **📋 Manual Step-by-Step (Alternative)**

#### **Step 1: Server Setup**
```bash
# On fresh Ubuntu 20.04+ server
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y nginx certbot python3-certbot-nginx redis-server docker.io docker-compose-v2

# Configure firewall
sudo ufw allow 22 && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw --force enable

# Add user to docker group
sudo usermod -aG docker $USER && newgrp docker
```

#### **Step 2: Clone and Configure**
```bash
# Clone repository
git clone https://github.com/yourusername/serp-loop-radio.git
cd serp-loop-radio

# Configure environment
cp env.template .env
nano .env  # Add your DataForSEO credentials and domain

# Example .env for production:
DATAFORSEO_LOGIN=your_login
DATAFORSEO_PASSWORD=your_password
ALLOWED_ORIGINS=https://your-domain.com,https://api.your-domain.com
LIVE_MODE_TOKEN=your-secure-token-here
REDIS_URL=redis://localhost:6379
```

#### **Step 3: SSL Certificate Setup**
```bash
# Copy Nginx configuration
sudo cp infra/nginx.conf /etc/nginx/sites-available/serp-loop-radio

# Edit with your domain
sudo nano /etc/nginx/sites-available/serp-loop-radio
# Replace 'your-domain.com' with your actual domain

# Enable site
sudo ln -sf /etc/nginx/sites-available/serp-loop-radio /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# Get SSL certificates (automatically configures nginx)
sudo certbot --nginx -d your-domain.com -d api.your-domain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

#### **Step 4: Start Services**
```bash
# Start Redis (persistent storage)
sudo systemctl enable redis-server && sudo systemctl start redis-server

# Start SERP Loop Radio
docker compose -f docker/docker-compose.yml up -d

# Verify health
curl https://api.your-domain.com/health
```

#### **Step 5: Frontend Configuration**
```bash
# Build frontend with production API endpoint
cd ui
echo "VITE_WS_URL=wss://api.your-domain.com/ws/serp" > .env.production
echo "VITE_API_KEY=your-secure-token-here" >> .env.production

npm run build

# Upload dist/ to Lovable or serve with nginx
```

---

## **🔒 Security & SSL Requirements**

### **Why WSS is Critical**
- Browsers **block unsecure WebSocket (ws://) connections** from HTTPS sites
- Mixed content policy requires **WSS (wss://)** for production
- CORS policies prevent cross-origin WebSocket without proper headers

### **Production Security Checklist**
- [ ] **SSL/TLS certificates** installed (Let's Encrypt or commercial)
- [ ] **WSS WebSocket** endpoints configured
- [ ] **CORS origins** restricted to your domains only
- [ ] **API tokens** rotated and secured
- [ ] **Rate limiting** enabled (10 req/s API, 5 req/s WebSocket)
- [ ] **Health monitoring** configured (`/health` endpoint)
- [ ] **Redis persistence** enabled (data survives restarts)
- [ ] **Audio limiter** prevents clipping (-1dBFS limit)

---

## **🔧 Advanced Configuration**

### **Environment Variables (Production)**
```bash
# Required for live mode
DATAFORSEO_LOGIN=your_dataforseo_login
DATAFORSEO_PASSWORD=your_dataforseo_password

# Security
ALLOWED_ORIGINS=https://yourdomain.com,https://api.yourdomain.com
LIVE_MODE_TOKEN=generate-secure-random-token-here

# Infrastructure  
REDIS_URL=redis://localhost:6379
FETCH_INTERVAL=90  # seconds between SERP data fetches

# Optional monitoring
SENTRY_DSN=your-sentry-dsn-for-error-tracking
LOG_LEVEL=INFO
```

### **Load Balancer Configuration**
```nginx
# For multiple backend instances
upstream serp_backend {
    server localhost:8000;
    server localhost:8001;  # Add more instances
    keepalive 32;
}

# Health check configuration
location /health {
    proxy_pass http://serp_backend/health;
    proxy_next_upstream error timeout http_500 http_502 http_503;
}
```

### **Monitoring & Alerts**
```bash
# Set up log monitoring
sudo journalctl -fu docker-compose@serp-loop-radio

# Health check monitoring (every 30s)
*/0.5 * * * * curl -f https://api.your-domain.com/health || echo "SERP Loop Radio down"

# Redis monitoring  
redis-cli --latency-history -i 1
```

---

## **📊 Go/No-Go Production Checklist**

### **✅ Pre-Production Validation**
```bash
# Test SSL/WSS connection
echo "Testing WSS connection..."
wscat -c wss://api.your-domain.com/ws/serp?api_key=YOUR_TOKEN&station=daily

# Verify CORS policy  
curl -H "Origin: https://unauthorized-domain.com" https://api.your-domain.com/health
# Should return CORS error

# Test audio limiter (no clipping)
# Load test with 10+ simultaneous events - meter should stay < 0dBFS

# Health check responds correctly
curl https://api.your-domain.com/health | jq '.status'
# Should return "ok"

# Rate limiting works
for i in {1..20}; do curl https://api.your-domain.com/health & done
# Some requests should get 429 Too Many Requests
```

### **🚦 Production Readiness Gates**
- [ ] **Green CI pipeline** (all tests pass)
- [ ] **WSS connection successful** from browser
- [ ] **Real DataForSEO data** fetching without errors  
- [ ] **Audio output** controlled (no clipping, appropriate volume)
- [ ] **Error monitoring** configured (Sentry/logs)
- [ ] **Backup/recovery** plan documented
- [ ] **DNS** configured (A records for domain and api subdomain)

---

## **🚨 Troubleshooting Common Issues**

### **WebSocket Connection Fails**
```bash
# Check SSL certificate
openssl s_client -connect api.your-domain.com:443 -servername api.your-domain.com

# Verify nginx WebSocket proxy
sudo nginx -t && sudo systemctl status nginx

# Check CORS headers
curl -I -H "Origin: https://your-domain.com" https://api.your-domain.com/ws/serp
```

### **Rate Limit Errors**
```bash
# Check DataForSEO API usage
# Dashboard: https://app.dataforseo.com/api-dashboard

# Adjust fetch interval (default 90s)
echo "FETCH_INTERVAL=120" >> .env && docker compose restart
```

### **Audio Issues**
```bash  
# Verify Tone.js limiter is active
# Browser DevTools -> Console should show: "Limiter active: -1dBFS"

# Check WebSocket message format
# DevTools -> Network -> WS tab -> inspect message payloads
```

---

## **🔄 Deployment Updates**

### **Zero-Downtime Updates**
```bash
# Pull latest changes
git pull origin main

# Update containers (rolling restart)
docker compose -f docker/docker-compose.yml up -d --no-deps api-server
docker compose -f docker/docker-compose.yml up -d --no-deps publisher

# Verify health after update  
curl https://api.your-domain.com/health
```

### **Rollback Procedure**
```bash
# Rollback to previous image version
docker compose -f docker/docker-compose.yml down
git checkout HEAD~1  # or specific commit
docker compose -f docker/docker-compose.yml up -d

# Verify rollback successful
curl https://api.your-domain.com/health | jq '.version'
```

---

## **📈 Production Monitoring**

### **Key Metrics to Track**
- **WebSocket connections**: Active connection count
- **API response time**: Health endpoint latency
- **Audio events/minute**: SERP change frequency
- **Redis memory usage**: Event queue size
- **DataForSEO API calls**: Rate limit compliance

### **Recommended Monitoring Stack**
- **Uptime**: UptimeRobot or Pingdom
- **Logs**: Sentry for error tracking
- **Metrics**: Grafana + Prometheus (optional)
- **Alerts**: Discord/Slack webhooks for critical issues

---

**🎵 Ready to go live? Run the production checklist above, then share your SERP Loop Radio URL with the world!** 