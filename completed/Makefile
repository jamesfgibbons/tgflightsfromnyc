# SERP Loop Radio MVP Makefile
.PHONY: help install dev test clean sample run deploy

# Default Python and pip commands
PYTHON := python3
PIP := pip3
VENV := .venv

# Help target
help:
	@echo "🎵 SERP Loop Radio MVP - Available Commands:"
	@echo ""
	@echo "Setup & Development:"
	@echo "  make install     - Install dependencies in virtual environment"
	@echo "  make dev         - Start local development environment"
	@echo "  make test        - Run tests with coverage"
	@echo "  make clean       - Clean temporary files and cache"
	@echo ""
	@echo "Audio Generation:"
	@echo "  make sample      - Generate sample audio from test data"
	@echo "  make run         - Run daily SERP collection and audio generation"
	@echo "  make preview     - Create preview from existing CSV"
	@echo ""
	@echo "Live Streaming (Phase 2):"
	@echo "  make live-setup  - Setup live streaming environment"
	@echo "  make live-dev    - Start live streaming in development mode"
	@echo "  make live-stop   - Stop live streaming services"
	@echo "  make live-test   - Test complete live system"
	@echo "  make test-publisher - Stream sample data for testing"
	@echo "  make test-stations  - Test station-specific events"
	@echo ""
	@echo "Production Deployment (Phase 3):"
	@echo "  make deploy-phase3  - Complete production deployment pipeline"
	@echo "  make deploy-server  - Deploy to production server"
	@echo "  make build-frontend - Build React app for production"
	@echo "  make deploy-frontend-rsync - Upload frontend via rsync"
	@echo "  make create-env-production - Create production environment file"
	@echo ""
	@echo "Testing & Validation:"
	@echo "  make smoke-test     - Full end-to-end smoke test"
	@echo "  make test-e2e       - Run Cypress tests"
	@echo "  make production-checklist - Production readiness validation"
	@echo "  make health-check   - Test API health endpoint"
	@echo "  make test-cors      - Validate CORS configuration"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy      - Deploy to AWS Lambda"
	@echo "  make docker      - Build Docker image"
	@echo ""
	@echo "Utilities:"
	@echo "  make check-deps  - Check audio dependencies (FluidSynth, etc.)"
	@echo "  make lint        - Run code linting"

# Install dependencies
install:
	@echo "📦 Setting up Python virtual environment..."
	$(PYTHON) -m venv $(VENV)
	@echo "📦 Installing dependencies..."
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt
	@echo "✅ Installation complete! Activate with: source $(VENV)/bin/activate"

# Development setup
dev: install
	@echo "🔧 Setting up development environment..."
	@if [ ! -f .env ]; then \
		echo "📝 Creating .env from template..."; \
		cp .env.template .env || echo "⚠️  Please create .env file manually"; \
	fi
	@echo "🎵 Development setup complete!"
	@echo "💡 Next steps:"
	@echo "   1. Edit .env with your API credentials"
	@echo "   2. Run 'make sample' to test audio generation"
	@echo "   3. Run 'make run' for full pipeline"

# Run tests
test:
	@echo "🧪 Running tests with coverage..."
	$(VENV)/bin/python -m pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing
	@echo "📊 Coverage report generated in htmlcov/"

# Generate sample audio
sample:
	@echo "🎵 Generating sample audio..."
	$(VENV)/bin/python -m src.cli sample
	@echo "🎧 Sample complete! Check /tmp/sample.mp3"

# Run daily pipeline
run:
	@echo "🚀 Running daily SERP Loop Radio pipeline..."
	$(VENV)/bin/python -m src.cli run-daily

# Create preview from CSV
preview:
	@echo "🎼 Creating audio preview..."
	@if [ -f data/sample.csv ]; then \
		$(VENV)/bin/python -m src.cli local-preview data/sample.csv --play; \
	else \
		echo "❌ No sample.csv found. Create one first or run 'make run'"; \
	fi

# Check audio dependencies
check-deps:
	@echo "🔍 Checking audio dependencies..."
	@echo "FluidSynth: $$(which fluidsynth || echo '❌ Not installed')"
	@echo "FFmpeg: $$(which ffmpeg || echo '❌ Not installed')"
	@echo ""
	@echo "📦 Installation hints:"
	@echo "  macOS: brew install fluidsynth ffmpeg"
	@echo "  Ubuntu: sudo apt-get install fluidsynth ffmpeg"

# Lint code
lint:
	@echo "🔍 Running code linting..."
	$(VENV)/bin/ruff check src/
	$(VENV)/bin/ruff format src/ --diff

# Clean temporary files
clean:
	@echo "🧹 Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache htmlcov/ .coverage
	rm -f /tmp/serp_*.mid /tmp/serp_*.mp3 /tmp/serp_*.wav /tmp/sample.*
	@echo "✅ Cleanup complete!"

# Build Docker image
docker:
	@echo "🐳 Building Docker image..."
	docker build -f docker/Dockerfile -t serp-loop-radio .
	@echo "✅ Docker image built: serp-loop-radio"

# Deploy to AWS (placeholder)
deploy:
	@echo "🚀 Deploying to AWS..."
	@echo "🚧 Lambda deployment not yet implemented in MVP"
	@echo "💡 For now, run the Docker image or use the CLI directly"

# Bootstrap everything
bootstrap: install check-deps sample
	@echo "🎉 Bootstrap complete!"
	@echo "🎵 SERP Loop Radio is ready to use!"

# End-to-end test
e2e: bootstrap
	@echo "🔄 Running end-to-end test..."
	@if [ -f data/sample.csv ]; then \
		make preview; \
		echo "🌐 Opening audio player..."; \
		open /tmp/preview.mp3 2>/dev/null || echo "🎧 Play /tmp/preview.mp3 to hear your SERP data!"; \
	else \
		echo "⚠️  No sample data found. Run 'make run' first to collect SERP data."; \
	fi

# ====== Phase 2: Live Streaming Commands ======

live-setup:
	@echo "🔧 Setting up live streaming environment..."
	@command -v docker >/dev/null 2>&1 || { echo "❌ Docker required but not installed"; exit 1; }
	@command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose required but not installed"; exit 1; }
	cd ui && npm install

live-dev:
	@echo "🎵 Starting SERP Loop Radio Live (development mode)..."
	docker-compose -f docker/docker-compose.yml up --build

live-stop:
	@echo "⏹️ Stopping live streaming services..."
	docker-compose -f docker/docker-compose.yml down

live-logs:
	@echo "📋 Viewing live streaming logs..."
	docker-compose -f docker/docker-compose.yml logs -f

redis-cli:
	@echo "🔴 Opening Redis CLI..."
	docker-compose -f docker/docker-compose.yml exec redis redis-cli

test-websocket:
	@echo "🧪 Testing WebSocket functionality..."
	$(VENV)/bin/python -m pytest tests/test_websocket.py -v

publisher-once:
	@echo "📡 Running publisher once..."
	$(VENV)/bin/python -m src.publisher --once

publisher-once-live:
	@echo "📡 Running publisher once with live data..."
	$(VENV)/bin/python -m src.publisher --once --live

publisher-continuous:
	@echo "📡 Starting continuous publisher..."
	$(VENV)/bin/python -m src.publisher

publisher-continuous-live:
	@echo "📡 Starting continuous publisher with live data..."
	$(VENV)/bin/python -m src.publisher --live

test-publisher:
	@echo "🧪 Starting test publisher with sample data..."
	$(VENV)/bin/python -m src.test_publisher --mode stream --simulate-changes

test-publisher-batch:
	@echo "📦 Publishing all sample data..."
	$(VENV)/bin/python -m src.test_publisher --mode batch

test-stations:
	@echo "📻 Testing station-specific events..."
	$(VENV)/bin/python -m src.test_publisher --mode stations

live-test:
	@echo "🎵 Testing complete live system..."
	@echo "Starting services..."
	docker-compose -f docker/docker-compose.yml up -d
	@echo "Waiting for services to be ready..."
	sleep 10
	@echo "Running tests..."
	$(MAKE) test-websocket
	@echo "Stopping services..."
	docker-compose -f docker/docker-compose.yml down

# ====== Phase 2.5: Production Readiness Commands ======

health-check:
	@echo "🔍 Testing health endpoint..."
	curl -f http://localhost:8000/health | jq '.' || echo "❌ Health check failed"

test-cors:
	@echo "🛡️ Testing CORS policy..."
	@echo "Testing unauthorized origin..."
	curl -H "Origin: https://unauthorized-domain.com" -I http://localhost:8000/health 2>/dev/null | grep -q "Access-Control-Allow-Origin" && echo "❌ CORS allows unauthorized origin" || echo "✅ CORS blocks unauthorized origin"

test-rate-limit:
	@echo "⚡ Testing rate limiting..."
	@echo "Sending 25 rapid requests..."
	@(for i in $$(seq 1 25); do curl -s -o /dev/null -w "%{http_code} " http://localhost:8000/health & done; wait; echo) | grep -q "429" && echo "✅ Rate limiting active" || echo "⚠️ Rate limiting not triggered"

validate-ssl:
	@echo "🔒 Validating SSL certificate..."
	@echo "Usage: make validate-ssl DOMAIN=your-domain.com"
	@if [ -z "$(DOMAIN)" ]; then echo "❌ Please set DOMAIN=your-domain.com"; exit 1; fi
	@echo "Testing SSL connection to $(DOMAIN)..."
	openssl s_client -connect $(DOMAIN):443 -servername $(DOMAIN) -verify_return_error < /dev/null 2>/dev/null && echo "✅ SSL certificate valid" || echo "❌ SSL certificate invalid"

test-wss:
	@echo "🔐 Testing WebSocket Secure connection..."
	@echo "Usage: make test-wss WSS_URL=wss://api.your-domain.com/ws/serp API_KEY=your-token"
	@if [ -z "$(WSS_URL)" ]; then echo "❌ Please set WSS_URL=wss://your-endpoint"; exit 1; fi
	@if [ -z "$(API_KEY)" ]; then echo "❌ Please set API_KEY=your-token"; exit 1; fi
	@command -v wscat >/dev/null 2>&1 || { echo "❌ Install wscat: npm install -g wscat"; exit 1; }
	@echo "Testing WSS connection..."
	timeout 10 wscat -c "$(WSS_URL)?api_key=$(API_KEY)&station=daily" -x 'ping' 2>/dev/null && echo "✅ WSS connection successful" || echo "❌ WSS connection failed"

test-audio-limiter:
	@echo "🔊 Testing audio limiter (prevent clipping)..."
	@echo "This requires manual verification in browser DevTools"
	@echo "1. Open browser DevTools -> Console"
	@echo "2. Connect to WebSocket endpoint"  
	@echo "3. Verify Tone.js limiter is active at -1dBFS"
	@echo "4. Check that peak meter never exceeds 0dBFS during stress test"

production-checklist:
	@echo "🚦 Production Readiness Checklist"
	@echo "=================================="
	@echo ""
	@echo "🔍 Automated Checks:"
	@printf "  Health endpoint: "
	@curl -s http://localhost:8000/health | jq -r '.status 2>/dev/null || echo "❌ FAILED"' | grep -q "ok" && echo "✅ OK" || echo "❌ FAILED"
	@printf "  Redis connection: "
	@docker exec serp-redis redis-cli ping 2>/dev/null | grep -q "PONG" && echo "✅ OK" || echo "❌ FAILED"
	@printf "  Redis persistence: "
	@docker exec serp-redis redis-cli config get save 2>/dev/null | grep -q "save" && echo "✅ OK" || echo "❌ NOT CONFIGURED"
	@printf "  CORS configured: "
	@curl -s -H "Origin: https://unauthorized.com" -I http://localhost:8000/health 2>/dev/null | grep -q "Access-Control-Allow-Origin" && echo "❌ TOO PERMISSIVE" || echo "✅ OK"
	@echo ""
	@echo "📋 Manual Checks Required:"
	@echo "  🔒 SSL certificate: make validate-ssl DOMAIN=yourdomain.com"
	@echo "  🔐 WSS connection: make test-wss WSS_URL=wss://api.yourdomain.com/ws/serp API_KEY=token"
	@echo "  🎵 Audio limiter: make test-audio-limiter (browser verification)"
	@echo "  📊 Frontend deployment: Lovable hosting with correct VITE_WS_URL"
	@echo "  🔑 Environment vars: Production values in .env"
	@echo ""
	@echo "🎯 Go/No-Go Criteria:"
	@echo "  - All automated checks pass ✅"
	@echo "  - SSL certificate valid 🔒"
	@echo "  - WSS connection works 🔐"
	@echo "  - Audio limiter prevents clipping 🔊"
	@echo "  - Frontend connects successfully 🌐"
	@echo "  - Real DataForSEO API tested 📊"

quick-prod-test:
	@echo "⚡ Quick Production Test Suite"
	@echo "============================="
	@$(MAKE) health-check
	@$(MAKE) test-cors
	@$(MAKE) test-rate-limit
	@echo ""
	@echo "✅ Quick tests complete. Run 'make production-checklist' for full validation."

# ====== Phase 3: Frontend Deployment Commands ======

build-frontend:
	@echo "🏗️ Building React frontend for production..."
	cd ui && npm run build
	@echo "✅ Frontend built in ui/dist/"

deploy-frontend-local:
	@echo "📁 Deploying frontend to local nginx directory..."
	@if [ ! -d "ui/dist" ]; then echo "❌ Frontend not built. Run 'make build-frontend' first"; exit 1; fi
	sudo mkdir -p /var/www/serpradio
	sudo cp -r ui/dist/* /var/www/serpradio/
	sudo chown -R www-data:www-data /var/www/serpradio
	@echo "✅ Frontend deployed to /var/www/serpradio"

deploy-frontend-rsync:
	@echo "🚀 Deploying frontend via rsync..."
	@echo "Usage: make deploy-frontend-rsync SERVER=your-server.com USER=username"
	@if [ -z "$(SERVER)" ]; then echo "❌ Please set SERVER=your-server"; exit 1; fi
	@if [ -z "$(USER)" ]; then echo "❌ Please set USER=username"; exit 1; fi
	@if [ ! -d "ui/dist" ]; then echo "❌ Frontend not built. Run 'make build-frontend' first"; exit 1; fi
	rsync -avz --delete ui/dist/ $(USER)@$(SERVER):/var/www/serpradio/
	@echo "✅ Frontend deployed to $(SERVER)"

create-env-production:
	@echo "🔐 Creating production environment file..."
	@if [ -f ".env.production" ]; then echo "⚠️ .env.production already exists"; exit 1; fi
	cp env.production.example .env.production
	@echo "📝 Edit .env.production with your actual credentials:"
	@echo "   - DataForSEO login/password"
	@echo "   - Generate secure tokens with: openssl rand -hex 32"
	@echo "   - Set CORS_ORIGINS=https://serpradio.com"

# Combined deployment command
deploy-production:
	@echo "🚀 Full Production Deployment"
	@echo "=============================="
	@$(MAKE) build-frontend
	@echo ""
	@echo "📋 Next steps:"
	@echo "1. Upload frontend: make deploy-frontend-rsync SERVER=159.223.153.111 USER=root"
	@echo "2. Copy nginx config: scp infra/nginx-serpradio.conf root@159.223.153.111:/etc/nginx/sites-available/serpradio"
	@echo "3. Copy production env: scp .env.production root@159.223.153.111:/opt/serpradio/"
	@echo "4. SSH to server and run deployment commands"

# ====== Phase 3: Testing & Validation ======

install-cypress:
	@echo "📦 Installing Cypress for end-to-end testing..."
	cd ui && npm install cypress --save-dev

test-e2e:
	@echo "🧪 Running Cypress end-to-end tests..."
	cd ui && npm run test:e2e

test-e2e-dev:
	@echo "🔍 Opening Cypress test runner..."
	cd ui && npm run test:e2e:dev

smoke-test:
	@echo "💨 Running smoke test suite..."
	@$(MAKE) live-dev &
	@sleep 30  # Wait for services to start
	@$(MAKE) test-publisher &
	@sleep 10  # Wait for test data
	cd ui && npm run test:e2e
	@$(MAKE) live-stop

# Server deployment commands
deploy-server:
	@echo "🚀 Deploying to production server..."
	@echo "Usage: make deploy-server SERVER=159.223.153.111"
	@if [ -z "$(SERVER)" ]; then echo "❌ Please set SERVER=your-ip"; exit 1; fi
	scp infra/scripts/deploy-serpradio.sh root@$(SERVER):/tmp/
	ssh root@$(SERVER) "chmod +x /tmp/deploy-serpradio.sh && /tmp/deploy-serpradio.sh"

# Full Phase 3 deployment pipeline
deploy-phase3:
	@echo "🎯 Phase 3: Complete Production Deployment"
	@echo "=========================================="
	@$(MAKE) create-env-production
	@$(MAKE) build-frontend
	@echo ""
	@echo "🔐 Next: Edit .env.production with your credentials"
	@echo "🚀 Then: make deploy-server SERVER=159.223.153.111"
	@echo "📊 Finally: make deploy-frontend-rsync SERVER=159.223.153.111 USER=root" 