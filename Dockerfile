# /Dockerfile

FROM python:3.13-slim-bookworm

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
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# ENV Path
ENV PATH="/root/.cargo/bin:$PATH"

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