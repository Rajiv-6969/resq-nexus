"""Block until DATABASE_URL answers `select 1` (up to two minutes)."""
import os
import sys
import time

from sqlalchemy import create_engine, text

url = os.environ["DATABASE_URL"]
for attempt in range(60):
    try:
        with create_engine(url).connect() as connection:
            connection.execute(text("select 1"))
        break
    except Exception as exc:  # noqa: BLE001  (any driver error: keep waiting)
        print(f"waiting for database ({attempt + 1}/60): {exc.__class__.__name__}", file=sys.stderr)
        time.sleep(2)
else:
    sys.exit("database never became ready")
