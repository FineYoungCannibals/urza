# /Dockerfile

FROM python:3.13-alpine

# Install system dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    linux-headers \
    libffi-dev \
    openssl-dev \
    mariadb-dev \
    mariadb-connector-c

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock* ./

# Install dependencies with uv
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Set Python path so imports work
ENV PYTHONPATH=/app

# Default command - run API server
CMD ["uv", "run", "uvicorn", "urza.api.app:app", "--host", "0.0.0.0", "--port", "8000"]