#!/bin/sh
# Docker entrypoint: optional asset check, wait for DB, apply migrations, start API.
set -e

# Fetch missing ONNX assets from release if network is available; does not fail if offline/deferred
python scripts/download_assets.py || echo "Asset fetch skipped or deferred; continuing with local assets."

# Wait for DB and apply migrations if DATABASE_URL is configured
python docker/wait_for_db.py

# Bind to Render's dynamic $PORT or fallback to 8000
PORT="${PORT:-8000}"
echo "Starting ResQ Nexus API on port ${PORT}..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT}"
