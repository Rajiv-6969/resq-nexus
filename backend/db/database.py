"""Database engine and sessions (SQLAlchemy 2).

The demo uses a SQLite file, backend/instance/resq_nexus.db (git-ignored). To use
PostgreSQL instead, install a driver (pip install "psycopg[binary]") and set
DATABASE_URL=postgresql+psycopg://user:password@host/dbname; the tables only use
portable column types, so nothing else changes.
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parent.parent
LOCAL_DB = BACKEND_DIR / "instance" / "resq_nexus.db"


class Base(DeclarativeBase):
    """Base class of every table."""


def database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if url.startswith("postgres://"):  # the short form many hosts hand out
        url = "postgresql://" + url.removeprefix("postgres://")
    if url:
        return url
    if os.getenv("VERCEL"):  # serverless functions can only write to /tmp
        return "sqlite:////tmp/resq_nexus.db"
    LOCAL_DB.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{LOCAL_DB.as_posix()}"


def make_engine(url: str) -> Engine:
    if not url.startswith("sqlite"):
        return create_engine(url, pool_pre_ping=True)
    engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 15})

    @event.listens_for(engine, "connect")
    def _enforce_foreign_keys(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


engine = make_engine(database_url())
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    with SessionLocal() as session:
        yield session


def seeding_enabled() -> bool:
    return os.getenv("SEED_DEMO_DATA", "1").strip().lower() not in {"0", "false", "no", "off"}


def init_db() -> None:
    """Create any missing tables; on an empty database, load the demo data."""
    from db import models  # noqa: F401  (registers the tables)
    from db.seed import seed_demo_data

    Base.metadata.create_all(engine)
    if seeding_enabled():
        with SessionLocal() as session:
            seed_demo_data(session)


def reset_database() -> None:
    """Drop every table and start again from the demo data (tests, or `python -m db.reset`)."""
    from db import models  # noqa: F401

    Base.metadata.drop_all(engine)
    init_db()
