# ResQ Nexus API. Build context = repository root (needs backend/ and data/).
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 RESQ_DATA_DIR=/app/data
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY data/ /app/data/
RUN chmod +x docker/entrypoint.sh
EXPOSE 8000
CMD ["./docker/entrypoint.sh"]
