# RISniper Dockerfile
# Build: docker build -t risniper .
# Run: docker run -d --env-file .env --name risniper risniper

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY data/.gitkeep ./data/

# Create non-root user for security
RUN useradd -m -u 1000 sniper && \
    chown -R sniper:sniper /app
USER sniper

# Environment variables (override with --env-file or -e)
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0,'.'); from src.config import config; print('OK')" || exit 1

# Run the bot
CMD ["python", "-m", "src.bot"]
