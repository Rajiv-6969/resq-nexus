# ResQ Nexus API. Build context = repository root (needs backend/ and data/).
FROM python:3.13-slim

# Container configuration and performance tuning:
# Disable Python bytecode caching, single-thread BLAS/OpenMP to prevent memory spikes
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RESQ_DATA_DIR=/app/data \
    PORT=8080 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

WORKDIR /app/backend

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source and data
COPY backend/ .
COPY data/ /app/data/

RUN chmod +x docker/entrypoint.sh

# Cloud Run defaults to 8080 (also expose 8000 for legacy/local testing)
EXPOSE 8080 8000

# Cloud Run injects dynamic $PORT (default 8080). Bind to 0.0.0.0 and dynamic $PORT.
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}"]

