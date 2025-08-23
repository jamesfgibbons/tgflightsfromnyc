# Caribbean Kokomo Pipeline Makefile
# Streamlined operations for SERP Radio production

.PHONY: help setup smoke ship validate clean status

# Default target
help:
	@echo "🏝️ Caribbean Kokomo Pipeline Operations"
	@echo ""
	@echo "Available targets:"
	@echo "  setup     - Install dependencies and setup environment"
	@echo "  smoke     - Run smoke test (fast validation)"
	@echo "  ship      - Run full acceptance test and ship"
	@echo "  validate  - Run all validation tools on existing catalog"
	@echo "  clean     - Clean up generated files"
	@echo "  status    - Show pipeline status and metrics"
	@echo ""
	@echo "Quick start:"
	@echo "  make setup    # First time setup"
	@echo "  make smoke    # Quick validation"
	@echo "  make ship     # Full production run"

# Setup environment and dependencies
setup:
	@echo "🔧 Setting up Caribbean Kokomo pipeline..."
	@python3 -m venv .venv 2>/dev/null || echo "venv already exists"
	@.venv/bin/pip install -r requirements.txt
	@echo "✅ Dependencies installed"
	@echo ""
	@echo "📝 Next steps:"
	@echo "1. Copy creds.env.example to creds.env.txt"
	@echo "2. Fill in your API keys (OpenAI, Supabase, Tequila)"
	@echo "3. Run the SQL schema in your Supabase database"
	@echo "4. Run 'make smoke' to test"

# Run smoke test (fast validation)
smoke:
	@echo "🏝️ Running smoke test..."
	@./scripts/smoke_test.sh
	@echo ""
	@echo "✅ Smoke test completed!"
	@echo "📊 Run 'make status' to see metrics"

# Run full acceptance test and ship to production
ship:
	@echo "🚢 Running full acceptance test..."
	@./scripts/acceptance_test.sh
	@echo ""
	@echo "🎉 Ready to ship!"
	@echo "🌐 Pipeline validated and catalog published"

# Validate existing catalog without running pipeline
validate:
	@echo "🔍 Validating existing catalog..."
	@if [ -f catalog.json ]; then \
		echo "📊 Validating catalog structure..."; \
		python tools/validate_catalog.py catalog.json; \
		echo "🎵 Checking audio files..."; \
		python tools/reconcile_catalog.py catalog.json; \
		echo "🔊 Checking audio levels..."; \
		python tools/lufs_check.py catalog.json; \
		echo "✅ Validation completed"; \
	else \
		echo "❌ catalog.json not found. Run 'make smoke' or 'make ship' first."; \
		exit 1; \
	fi

# Show pipeline status and metrics
status:
	@echo "📊 Caribbean Kokomo Pipeline Status"
	@echo "=================================="
	@if [ -f catalog.json ]; then \
		TRACK_COUNT=$$(python -c "import json; data=json.load(open('catalog.json')); print(len(data.get('tracks', [])))"); \
		CARIBBEAN_COUNT=$$(python -c "import json; data=json.load(open('catalog.json')); caribbean_routes=[t for t in data.get('tracks', []) if any(dest in t.get('route', '') for dest in ['STT', 'STI', 'STX', 'SJU', 'MBJ', 'CUR', 'AUA'])]; print(len(caribbean_routes))"); \
		JACKPOT_COUNT=$$(python -c "import json; data=json.load(open('catalog.json')); jackpots=[t for t in data.get('tracks', []) if float(t.get('price', 999)) < 85]; print(len(jackpots))"); \
		PRICE_RANGE=$$(python -c "import json; data=json.load(open('catalog.json')); prices=[float(t.get('price', 0)) for t in data.get('tracks', []) if t.get('price')]; print(f'{min(prices):.0f}-{max(prices):.0f}' if prices else '0-0')"); \
		echo "📊 Catalog Metrics:"; \
		echo "   Total tracks: $$TRACK_COUNT"; \
		echo "   Caribbean routes: $$CARIBBEAN_COUNT"; \
		echo "   Jackpot deals (< \$$85): $$JACKPOT_COUNT"; \
		echo "   Price range: \$$$$PRICE_RANGE"; \
		echo "   Last updated: $$(stat -f %Sm catalog.json)"; \
	else \
		echo "❌ No catalog found. Run 'make smoke' or 'make ship' to generate."; \
	fi
	@echo ""
	@echo "🔧 Environment:"
	@if [ -f creds.env.txt ]; then \
		echo "   ✅ Credentials configured"; \
	else \
		echo "   ❌ Credentials missing (need creds.env.txt)"; \
	fi
	@if [ -d .venv ]; then \
		echo "   ✅ Virtual environment ready"; \
	else \
		echo "   ❌ Virtual environment missing (run 'make setup')"; \
	fi

# Clean up generated files
clean:
	@echo "🧹 Cleaning up generated files..."
	@rm -f catalog.json
	@rm -f *.log
	@echo "✅ Cleanup completed"

# Development shortcuts
dev-smoke: smoke status
dev-ship: ship status