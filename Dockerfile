# /Dockerfile

FROM python:3.13-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libmariadb-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv (binary installation only)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Urza user creation
RUN groupadd -g 1000 urza && \
    useradd -u 1000 -g urza -m -s /bin/bash urza

RUN chown -R root:1000 /app && \
    chmod 770 /app


# Copy project files
COPY --chown=urza:urza pyproject.toml uv.lock* ./

# Sync as user urza
USER urza

# Copy project files
RUN uv sync --frozen --no-dev

# Copy application code
COPY --chown=urza:urza . .

# Set Python path so imports work
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

# Default command - run API server
CMD ["uv", "run", "uvicorn", "urza.api.app:app", "--host", "0.0.0.0", "--port", "8000"]