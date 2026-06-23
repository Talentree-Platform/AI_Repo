# ============================================================
# Talentree AI Service — Dockerfile
# Python 3.12 + ODBC Driver 17 for SQL Server
# Target: Azure App Service for Containers (port 8000)
# ============================================================
FROM python:3.12-slim

# Install system dependencies for pyodbc + ODBC Driver 17
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg2 \
    apt-transport-https \
    unixodbc-dev \
    gcc \
    g++ \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
       | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
       > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create models directory if not present
RUN mkdir -p models data/csv

# ── Port ──────────────────────────────────────────────────────
# Azure App Service expects port 8000 (set via WEBSITES_PORT=8000 in App Settings)
# DO NOT use port 7860 (that was Hugging Face Spaces only)
EXPOSE 8000

# Health check — Azure also pings / so keep /ai/status as secondary
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/ai/status || exit 1

# ── Start ─────────────────────────────────────────────────────
# Single worker: APScheduler must run in exactly 1 process
# (multiple workers = scheduler fires N times per job)
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
