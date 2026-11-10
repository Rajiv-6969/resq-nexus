"""Location column: a PostGIS POINT (SRID 4326) on PostgreSQL, WKT text elsewhere.

Every table with a position keeps ``latitude`` / ``longitude`` floats (the API reads
them) and also stores ``location``: on PostgreSQL a PostGIS geometry with a spatial
index, so radius searches use ST_DWithin; on SQLite (tests, quick local runs without
Docker) the same value as EWKT text and radius searches fall back to a bounding box.
"""
from __future__ import annotations

from typing import Any

from geoalchemy2 import Geography, Geometry
from geoalchemy2.functions import ST_DWithin, ST_MakePoint, ST_SetSRID
from sqlalchemy import String, cast, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.sql import ColumnElement

from services.geo import bounding_box

SRID = 4326
GEOGRAPHY = Geography(geometry_type="GEOMETRY", srid=SRID)  # metres-based distance on the sphere


def is_postgres(url: str) -> bool:
    return url.startswith("postgresql")


def location_type(url: str):
    """Column type for ``location`` given the database URL."""
    if is_postgres(url):
        return Geometry(geometry_type="POINT", srid=SRID, spatial_index=True)
    return String(64)


def ewkt_point(lat: float, lon: float) -> str:
    return f"SRID={SRID};POINT({lon} {lat})"


def register_location_sync(*models: type) -> None:
    """Keep ``location`` equal to (latitude, longitude) on insert and update."""

    def _sync(_mapper, _connection, target: Any) -> None:
        if target.latitude is None or target.longitude is None:
            return
        attrs = inspect(target).attrs
        if target.location is None or attrs.latitude.history.has_changes() or attrs.longitude.history.has_changes():
            target.location = ewkt_point(target.latitude, target.longitude)

    for model in models:
        event.listen(model, "before_insert", _sync)
        event.listen(model, "before_update", _sync)


def within_radius(model: type, lat: float, lon: float, radius_km: float, engine: Engine) -> ColumnElement:
    """SQL filter for rows within radius_km of (lat, lon): PostGIS ST_DWithin, else a bounding box.

    The caller still sorts and trims by exact haversine distance, so both paths return
    the same rows.
    """
    if engine.dialect.name == "postgresql":
        here = cast(ST_SetSRID(ST_MakePoint(lon, lat), SRID), GEOGRAPHY)
        return ST_DWithin(cast(model.location, GEOGRAPHY), here, radius_km * 1000)
    south, north, west, east = bounding_box(lat, lon, radius_km)
    return model.latitude.between(south, north) & model.longitude.between(west, east)
