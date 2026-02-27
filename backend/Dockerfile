# Pin base image with digest for security (python:3.12-slim)
# Update digest periodically: docker pull python:3.12-slim && docker inspect python:3.12-slim | grep Id
FROM python:3.12-slim@sha256:9e01bf1ae5db7649a236da7be1e94ffbbbdd7a93f867dd0d8d5720d9e1f89fab

# Install uv — pin version to match CI (UV_VERSION in ci.yml); update both together.
COPY --from=ghcr.io/astral-sh/uv:0.10.6 /uv /usr/local/bin/uv

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl gosu && \
    rm -rf /var/lib/apt/lists/*

# Copy only dependency definition files first for layer caching.
# uv.lock ensures reproducible builds — run `make lock` after editing pyproject.toml.
COPY pyproject.toml uv.lock ./

# Install production dependencies only (no dev deps, no project install)
RUN uv sync --frozen --no-dev --no-install-project

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
CMD ["uv", "run", "--frozen", "--no-dev", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
