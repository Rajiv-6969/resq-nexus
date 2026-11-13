# ResQ Nexus API. Build context = repository root (needs backend/ and data/).
FROM python:3.13-slim

# Memory optimization for 512 MB Render free-tier container:
# Disable Python bytecode caching, single-thread BLAS/OpenMP to prevent memory spikes
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RESQ_DATA_DIR=/app/data \
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

EXPOSE 8000

CMD ["./docker/entrypoint.sh"]
