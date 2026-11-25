#!/bin/sh
# Docker entrypoint: optional asset check, wait for DB, apply migrations, start API.
set -e

# Fetch missing ONNX assets from release if network is available; does not fail if offline/deferred
python scripts/download_assets.py || echo "Asset fetch skipped or deferred; continuing with local assets."

# Wait for DB and apply migrations if DATABASE_URL is configured
if [ -n "$DATABASE_URL" ]; then
    python docker/wait_for_db.py || echo "Warning: DB wait timed out or failed; proceeding to start API."
fi

# Bind to Cloud Run's dynamic $PORT or fallback to 8080
PORT="${PORT:-8080}"
echo "Starting ResQ Nexus API on port ${PORT}..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT}"
