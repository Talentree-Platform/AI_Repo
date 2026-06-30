FROM python:3.10-slim

# Install system dependencies and Microsoft SQL Server ODBC Driver requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg2 \
    apt-transport-https \
    ca-certificates \
    unixodbc \
    unixodbc-dev \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Add Microsoft package repository and install ODBC drivers 17 and 18
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /etc/apt/trusted.gpg.d/microsoft.gpg \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --pre --no-cache-dir -r requirements.txt || pip install --no-cache-dir -r requirements.txt

# Copy all codebase files
COPY . .

# Grant full read/write permissions for Hugging Face Spaces non-root user (UID 1000)
RUN chmod -R 777 /app

# Hugging Face Spaces runs on port 7860
EXPOSE 7860

CMD ["python", "main.py"]
