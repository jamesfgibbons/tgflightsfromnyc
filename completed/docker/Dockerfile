# SERP Loop Radio MVP - Docker Image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    fluidsynth \
    ffmpeg \
    wget \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Download a free soundfont
RUN mkdir -p /app/assets && \
    wget -O /app/assets/FluidR3_GM.sf2 \
    "https://archive.org/download/FluidR3Gm/FluidR3%20GM.sf2" || \
    wget -O /app/assets/FluidR3_GM.sf2 \
    "https://musical-artifacts.com/artifacts/618/FluidR3_GM.sf2" || \
    echo "Warning: Could not download soundfont, audio quality may be reduced"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY config/ config/

# Copy entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set environment variables
ENV PYTHONPATH=/app
ENV TMP_DIR=/tmp
ENV FLUIDSYNTH_SOUNDFONT=/app/assets/FluidR3_GM.sf2

# Create directories for temporary files
RUN mkdir -p /tmp /app/data /app/output

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import src.cli; print('Service healthy')" || exit 1

# Default entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command - can be overridden
CMD ["run-daily"] 