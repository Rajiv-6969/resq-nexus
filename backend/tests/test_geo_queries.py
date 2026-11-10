"""Radius queries: the SQLite path (bounding box + Python haversine) must return exactly what
PostGIS would, and the PostgreSQL path must compile to ST_DWithin."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.dialects import postgresql

import main
from db.database import SessionLocal, engine
from db.geo import ewkt_point, within_radius
from db.models import Resource
from services.geo import haversine_km, sort_by_distance
from tests.conftest import demo_headers

client = TestClient(main.app)

ORIGINS = [(12.9716, 77.5946, 5), (12.9716, 77.5946, 10), (12.90, 77.65, 25), (26.1, 91.7, 50), (12.95, 77.60, 0.5)]


@pytest.mark.parametrize("lat,lon,radius", ORIGINS)
def test_sqlite_radius_filter_matches_pure_haversine(fresh_db, lat, lon, radius):
    with SessionLocal() as db:
        every = list(db.scalars(select(Resource)))
        filtered = list(db.scalars(select(Resource).where(within_radius(Resource, lat, lon, radius, engine))))
    expected = [r.id for r, _ in sort_by_distance(every, lat, lon, key=lambda r: (r.latitude, r.longitude),
                                                  name=lambda r: r.name, radius_km=radius)]
    got = [r.id for r, _ in sort_by_distance(filtered, lat, lon, key=lambda r: (r.latitude, r.longitude),
                                             name=lambda r: r.name, radius_km=radius)]
    assert got == expected  # same rows, same nearest-first order


def test_nearby_endpoint_distances_are_haversine(fresh_db):
    lat, lon = 12.9716, 77.5946
    headers = demo_headers(client, "CITIZEN")
    body = client.get("/resources/nearby", params={"lat": lat, "lon": lon, "radius_km": 10}, headers=headers).json()
    assert body["count"] > 0
    distances = [r["distance_km"] for r in body["resources"]]
    assert distances == sorted(distances) and all(d <= 10 for d in distances)
    for r in body["resources"]:
        assert r["distance_km"] == round(haversine_km(lat, lon, r["latitude"], r["longitude"]), 2)


def test_location_column_mirrors_lat_lon(fresh_db):
    with SessionLocal() as db:
        r = db.scalars(select(Resource)).first()
        assert r.location == ewkt_point(r.latitude, r.longitude)
        r.latitude += 0.01
        db.commit()
        db.refresh(r)
        assert r.location == ewkt_point(r.latitude, r.longitude)


def test_postgres_path_uses_st_dwithin():
    pg = create_engine("postgresql+psycopg://u:p@localhost/x")
    sql = str(select(Resource.id).where(within_radius(Resource, 12.9, 77.6, 10, pg)).compile(dialect=postgresql.dialect()))
    assert "ST_DWithin" in sql and "geography" in sql and "ST_MakePoint" in sql
    assert "between" not in sql.lower()
