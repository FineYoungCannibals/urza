# /Dockerfile

FROM python:3.13-slim-bookworm

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libmariadb-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# ENV Path
ENV PATH="/root/.local/bin:$PATH"
SHELL ["/bin/bash", "-c"]

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Set Python path so imports work
ENV PYTHONPATH=/app

# Default command - run API server
CMD ["uv", "run", "uvicorn", "urza.api.app:app", "--host", "0.0.0.0", "--port", "8000"]