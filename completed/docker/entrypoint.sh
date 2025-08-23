#!/bin/bash
set -e

# SERP Loop Radio Docker Entrypoint
echo "🎵 Starting SERP Loop Radio..."

# Check for required environment variables
if [ -z "$DATAFORSEO_LOGIN" ] && [ "$1" != "sample" ] && [ "$1" != "local-preview" ]; then
    echo "⚠️  Warning: DATAFORSEO_LOGIN not set. Some commands may fail."
fi

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Set Python path
export PYTHONPATH=/app:$PYTHONPATH

# Handle different commands
case "$1" in
    run-daily)
        echo "🚀 Running daily SERP collection and audio generation..."
        python -m src.cli run-daily
        ;;
    run-weekly)
        echo "📅 Running weekly batch processing..."
        python -m src.cli run-weekly
        ;;
    sample)
        echo "🎵 Generating sample audio..."
        python -m src.cli sample
        ;;
    local-preview)
        echo "🎼 Creating audio preview..."
        if [ -n "$2" ]; then
            python -m src.cli local-preview "$2"
        else
            echo "❌ Please provide CSV file path"
            exit 1
        fi
        ;;
    call-dataforseo-status)
        echo "📊 Checking DataForSEO API status..."
        python -m src.cli call-dataforseo-status
        ;;
    bash)
        echo "🐚 Starting interactive shell..."
        exec /bin/bash
        ;;
    help)
        echo "🎵 SERP Loop Radio Docker Commands:"
        echo "  run-daily              - Run daily SERP collection and audio generation"
        echo "  run-weekly             - Run weekly batch processing"
        echo "  sample                 - Generate sample audio from test data"
        echo "  local-preview <csv>    - Create audio preview from CSV file"
        echo "  call-dataforseo-status - Check DataForSEO API status"
        echo "  bash                   - Start interactive shell"
        echo "  help                   - Show this help message"
        ;;
    *)
        # If it's a Python CLI command, pass it through
        if python -m src.cli --help | grep -q "$1"; then
            echo "🎵 Running command: $*"
            python -m src.cli "$@"
        else
            echo "❌ Unknown command: $1"
            echo "Run 'help' to see available commands"
            exit 1
        fi
        ;;
esac

echo "✅ Command completed successfully!" 