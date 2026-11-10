"""Alembic environment: reads DATABASE_URL (backend/.env or the environment)."""
from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from db.database import Base, database_url  # noqa: E402
from db import models  # noqa: E402, F401  (registers the tables)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
config.set_main_option("sqlalchemy.url", database_url())
target_metadata = Base.metadata


def include_object(obj, name, type_, reflected, compare_to):
    # PostGIS' own table must never be touched by autogenerate.
    return not (type_ == "table" and name == "spatial_ref_sys")


def run_migrations_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata,
                      literal_binds=True, include_object=include_object)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(config.get_section(config.config_ini_section, {}),
                                     prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, include_object=include_object)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
