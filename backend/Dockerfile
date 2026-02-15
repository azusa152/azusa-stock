# Pin base image with digest for security (python:3.12-slim)
# Update digest periodically: docker pull python:3.12-slim && docker inspect python:3.12-slim | grep Id
FROM python:3.12-slim@sha256:9e01bf1ae5db7649a236da7be1e94ffbbbdd7a93f867dd0d8d5720d9e1f89fab

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl gosu && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directories and set permissions
RUN mkdir -p /app/data /app/data/logs /app/data/yf_cache

# Create non-root user for security
RUN groupadd -r folio && useradd -r -g folio folio && \
    chown -R folio:folio /app

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
