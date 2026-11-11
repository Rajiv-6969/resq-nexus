"""Nearby resources: haversine distance, sorting, radius and type filters."""
import math

import pytest
from fastapi.testclient import TestClient

import main
from conftest import demo_headers
from services.geo import haversine_km, sort_by_distance

client = TestClient(main.app)
KORAMANGALA = (12.93574, 77.62408)


def reference_km(lat1, lon1, lat2, lon2):
    """Independent spherical-law-of-cosines distance, to check the API's numbers."""
    p1, p2, dl = math.radians(lat1), math.radians(lat2), math.radians(lon2 - lon1)
    cos_c = math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)
    return 6371.0088 * math.acos(max(-1.0, min(1.0, cos_c)))


@pytest.fixture(autouse=True)
def _db(fresh_db):
    yield


@pytest.fixture
def citizen():
    return demo_headers(client, "CITIZEN")


def nearby(headers, lat=KORAMANGALA[0], lon=KORAMANGALA[1], **params):
    return client.get("/resources/nearby", params={"lat": lat, "lon": lon, **params}, headers=headers)


# --------------------------------------------------------------------------- haversine
def test_haversine_matches_known_distances():
    assert haversine_km(51.5074, -0.1278, 48.8566, 2.3522) == pytest.approx(343.6, abs=0.5)  # London - Paris
    assert haversine_km(12.9716, 77.5946, 13.0827, 80.2707) == pytest.approx(290.2, abs=1.0)  # Bengaluru - Chennai


def test_haversine_is_zero_for_the_same_point_and_symmetric():
    assert haversine_km(23.3, 70.35, 23.3, 70.35) == 0
    assert haversine_km(12.9, 77.6, 23.3, 70.3) == pytest.approx(haversine_km(23.3, 70.3, 12.9, 77.6))


def test_sort_by_distance_orders_nearest_first_and_breaks_ties_by_name():
    items = [
        {"name": "Far", "latitude": 13.10, "longitude": 77.60},
        {"name": "Near B", "latitude": 12.94, "longitude": 77.62},
        {"name": "Near A", "latitude": 12.94, "longitude": 77.62},
        {"name": "Middle", "latitude": 12.98, "longitude": 77.64},
    ]
    ranked = sort_by_distance(items, 12.935, 77.624, key=lambda item: (item["latitude"], item["longitude"]),
                              name=lambda item: item["name"])
    assert [item["name"] for item, _ in ranked] == ["Near A", "Near B", "Middle", "Far"]
    distances = [d for _, d in ranked]
    assert distances == sorted(distances)


# --------------------------------------------------------------------------- API
def test_nearby_resources_are_sorted_by_real_distance(citizen):
    body = nearby(citizen, radius_km=10).json()
    resources = body["resources"]
    assert body["count"] == len(resources) > 5
    distances = [r["distance_km"] for r in resources]
    assert distances == sorted(distances)
    assert all(d <= 10 for d in distances)
    for r in resources:
        assert r["distance_km"] == pytest.approx(reference_km(*KORAMANGALA, r["latitude"], r["longitude"]), abs=0.01)
    assert resources[0]["area"] == "Koramangala"


def test_radius_limits_the_results(citizen):
    small = nearby(citizen, radius_km=2).json()["resources"]
    large = nearby(citizen, radius_km=25).json()["resources"]
    assert 0 < len(small) < len(large)
    assert {r["id"] for r in small} <= {r["id"] for r in large}


def test_type_filter_keeps_only_the_chosen_types(citizen):
    body = nearby(citizen, radius_km=25, types="HOSPITAL,SHELTER").json()
    assert body["resources"]
    assert {r["resource_type"] for r in body["resources"]} == {"HOSPITAL", "SHELTER"}


def test_each_resource_shows_availability_status_contact_and_update_time(citizen):
    hospital = next(r for r in nearby(citizen, radius_km=25).json()["resources"] if r["resource_type"] == "HOSPITAL")
    assert hospital["unit"] == "beds"
    assert 0 <= hospital["capacity_available"] <= hospital["capacity_total"]
    assert hospital["status"] in {"OPEN", "FULL", "CLOSED"}
    assert hospital["contact_phone"].startswith("+91")
    assert hospital["updated_at"]


def test_scenario_regions_have_resources_too(citizen):
    tapovan = nearby(citizen, lat=30.49, lon=79.63, radius_km=50).json()["resources"]
    assert {"HOSPITAL", "SHELTER", "FIRE_STATION"} <= {r["resource_type"] for r in tapovan}
    assert any(r["name"] == "Tapovan Field Hospital" and r["status"] == "FULL" for r in tapovan)
    assert any(r["source"] == "osm" and r["osm_id"] for r in tapovan)  # real OpenStreetMap facilities sit next to the seed


def test_nothing_nearby_returns_an_empty_list(citizen):
    body = nearby(citizen, lat=10.0, lon=60.0, radius_km=50).json()  # Arabian Sea
    assert body == {"origin": {"latitude": 10.0, "longitude": 60.0}, "radius_km": 50.0, "count": 0, "resources": []}


@pytest.mark.parametrize(
    "params",
    [{"radius_km": 0}, {"radius_km": 501}, {"types": "HOSPITAL,SPACEPORT"}, {"lat": 95}, {"lon": 190}],
)
def test_invalid_queries_are_rejected(citizen, params):
    assert nearby(citizen, **params).status_code == 422


@pytest.mark.parametrize("role", ["CITIZEN", "SERVICE_PROVIDER", "ADMIN"])
def test_every_role_can_look_up_nearby_resources(role):
    assert nearby(demo_headers(client, role)).status_code == 200


def test_nearby_resources_need_a_login():
    assert nearby(None).status_code == 401
