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

# Trust corporate root CAs when any .crt files are supplied in certs/.
# Chromium on Linux reads its own NSS store, so the certs go to both places.
COPY certs/ /usr/local/share/ca-certificates/
RUN if ls /usr/local/share/ca-certificates/*.crt >/dev/null 2>&1; then \
        update-ca-certificates && \
        apt-get update && apt-get install -y --no-install-recommends libnss3-tools && \
        rm -rf /var/lib/apt/lists/* && \
        mkdir -p /root/.pki/nssdb && \
        certutil -d sql:/root/.pki/nssdb -N --empty-password 2>/dev/null || true && \
        for c in /usr/local/share/ca-certificates/*.crt; do \
            certutil -d sql:/root/.pki/nssdb -A -t "C,," -n "$(basename "$c")" -i "$c"; \
        done; \
    fi

# Copy application code
COPY . .

# Create directory for screenshots
RUN mkdir -p /tmp/screenshots

# App Service overrides PORT; default keeps Container Apps working unchanged
ENV PORT=8000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Run the application
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
