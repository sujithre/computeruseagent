# Use the official Playwright image with Python
FROM mcr.microsoft.com/playwright/python:v1.57.0-jammy

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# certutil is needed to add corporate CAs to Chromium's NSS store at startup
RUN apt-get update \
    && apt-get install -y --no-install-recommends libnss3-tools \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . .
RUN chmod +x /app/entrypoint.sh

# Create directory for screenshots
RUN mkdir -p /tmp/screenshots

# App Service overrides PORT; default keeps Container Apps working unchanged
ENV PORT=8000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Run the application
CMD ["/app/entrypoint.sh"]
