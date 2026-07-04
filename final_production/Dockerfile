FROM python:3.11-slim

# Set environment paths and variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install system dependencies (build-essential and FreeTDS are required for building and running pymssql)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    freetds-bin \
    freetds-dev \
    libsybdb5 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/

# Expose API serving port
EXPOSE 8000

# Start Uvicorn Server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
