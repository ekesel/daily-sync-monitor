# ============================================================
# 1) Build stage (installs deps)
# ============================================================
FROM python:3.11-slim AS builder

# Prevent Python from writing .pyc files, force stdout/stderr unbuffered
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (if you use Postgres, MSSQL clients, etc. add here)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps into a local directory
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --prefix=/install -r requirements.txt

# ============================================================
# 2) Runtime stage (minimal image)
# ============================================================
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy installed packages from builder layer
COPY --from=builder /install /usr/local

# Copy application code
COPY app ./app

# Default environment (override in real envs)
# APP_ENV=local for dev, APP_ENV=prod in production
ENV APP_ENV=prod

# Expose the port Uvicorn will listen on
EXPOSE 8000

# Healthcheck (optional but recommended)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS http://localhost:8000/health || exit 1

# Run FastAPI app with Uvicorn
# If your main app object is `app` in app/main.py, this is correct: "app.main:app"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]