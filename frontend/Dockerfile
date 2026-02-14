# Pin base image with digest for security (python:3.12-slim)
# Update digest periodically: docker pull python:3.12-slim && docker inspect python:3.12-slim | grep Id
FROM python:3.12-slim@sha256:2fba8e70a87bcc9f6edd20dda0a1d4adb32046d2acbca7361bc61da5a106a0f7

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user for security
RUN groupadd -r folio && useradd -r -g folio folio && \
    chown -R folio:folio /app

USER folio

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
