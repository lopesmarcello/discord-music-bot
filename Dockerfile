FROM python:3.12-slim

# Install FFmpeg and system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency manifest and install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy bot source
COPY bot/ bot/

CMD ["python", "-m", "bot"]
