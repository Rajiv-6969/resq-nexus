#!/bin/sh
# Docker entrypoint: wait for PostgreSQL, apply migrations, start the API.
set -e
python docker/wait_for_db.py
exec uvicorn main:app --host 0.0.0.0 --port 8000
