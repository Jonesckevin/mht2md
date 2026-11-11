# Upgrade from python:3.9 to python:3.12 to enable Pillow>=12.3.0
# (Pillow 12.x requires Python >= 3.10; fixes 13 HIGH CVEs)
FROM python:3.15-slim

# Set the working directory in the container
WORKDIR /app

# Upgrade system packages to fix CRITICAL CVEs (CVE-2026-31789: OpenSSL)
# and all other fixable Debian package vulnerabilities before copying app code
RUN apt-get update && apt-get upgrade -y --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Copy the application files to the container
COPY . /app

# Create an uploads directory
RUN mkdir -p /app/uploads && \
    groupadd -r -g 1000 appuser && useradd -r -u 1000 -g appuser appuser && \
    chown -R appuser:appuser /app

# Install the required Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Set the FLASK_APP environment variable to point to the app module
ENV FLASK_APP=/app/app.py

USER appuser

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/').close()" || exit 1

CMD ["flask", "run", "--host=0.0.0.0", "--port=8080", "--reload"]
