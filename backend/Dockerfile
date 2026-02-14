# Pin base image with digest for security (python:3.12-slim)
# Update digest periodically: docker pull python:3.12-slim && docker inspect python:3.12-slim | grep Id
FROM python:3.12-slim@sha256:2fba8e70a87bcc9f6edd20dda0a1d4adb32046d2acbca7361bc61da5a106a0f7

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create data directories and set permissions
RUN mkdir -p /app/data /app/data/logs

# Create non-root user for security
# IMPORTANT: Volume permissions — Docker named volumes inherit directory permissions
# on first creation. If upgrading from a root-based container, reset volumes with:
# docker compose down -v && docker compose up --build
RUN groupadd -r folio && useradd -r -g folio folio && \
    chown -R folio:folio /app

USER folio

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
