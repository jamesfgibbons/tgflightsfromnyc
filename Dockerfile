# Pin to Python 3.11 for consistent runtime
FROM python:3.11-slim

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fluidsynth \
    fluid-soundfont-gm \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Verify audio tools are available
RUN which ffmpeg && which fluidsynth && ls /usr/share/sounds/sf2/

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# Set environment variables
ENV PYTHONPATH=/app
ENV SOUNDFONT_PATH=/usr/share/sounds/sf2/FluidR3_GM.sf2

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/healthz || exit 1

# Expose port
EXPOSE 8000

# Run the application (honor Railway/Heroku style $PORT, default 8000)
CMD ["/bin/sh", "-lc", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
