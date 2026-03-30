# ============================================
# Error Gateway - Dockerfile
# ============================================
# Python 3.13 + FastAPI + uv
# ============================================

# --------------------------------------------
# Stage 1: Builder
# --------------------------------------------
FROM python:3.13.1-slim-bookworm AS builder

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependencies
COPY pyproject.toml uv.lock* ./

# Install production dependencies only
RUN uv pip install --system --no-cache -e "."

# --------------------------------------------
# Stage 2: Production
# --------------------------------------------
FROM python:3.13.1-slim-bookworm AS production

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user ПЕРЕД копированием файлов
RUN useradd -m -u 1000 appuser

# Copy dependencies from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy source code с правильными правами
COPY --chown=appuser:appuser . .

# Переключиться на non-root пользователя
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
