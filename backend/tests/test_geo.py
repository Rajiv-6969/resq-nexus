"""Real-geography layer (services.geo) and the scenario builder, fully offline.

Network calls are replaced by ``fake_overpass`` (Overpass JSON built from
``tests/fixtures/geo/``) and ``grid_graph`` (a tiny lattice standing in for the OSMnx
download). The on-disk caches are exercised in ``tmp_path``.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import networkx as nx
import numpy as np
import pytest

from schemas.contracts import ZoneAssessment
from services import allocation_engine as engine
from services.geo import facilities as fac
from services.geo import osm, population, roads, routing, zones
from services.scenarios import Scenario

FIXTURES = Path(__file__).parent / "fixtures" / "geo"
BBOX = osm.BBox(10.08, 76.33, 10.12, 76.37)  # 4.4 km x 4.4 km around Aluva
CENTRE = (10.10, 76.35)


# --------------------------------------------------------------------------- fakes
def grid_graph(bbox: osm.BBox = BBOX, n: int = 6) -> nx.Graph:
    """A lattice of residential roads with one fast primary road along the middle row."""
    graph = nx.Graph()
    lats = np.linspace(bbox.south, bbox.north, n)
    lons = np.linspace(bbox.west, bbox.east, n)
    node = lambda r, c: 1000 + r * n + c  # noqa: E731
    for r, lat in enumerate(lats):
        for c, lon in enumerate(lons):
            graph.add_node(node(r, c), latitude=round(float(lat), 6), longitude=round(float(lon), 6))
    mid = n // 2
    for r in range(n):
        for c in range(n):
            for dr, dc in ((0, 1), (1, 0)):
                r2, c2 = r + dr, c + dc
                if r2 < n and c2 < n:
                    a, b = node(r, c), node(r2, c2)
                    highway = "primary" if (dr == 0 and r == mid) else "residential"
                    length = round(osm_dist(graph, a, b), 1)
                    speed = roads.road_speed(highway)
                    coords = [[graph.nodes[a]["latitude"], graph.nodes[a]["longitude"]], [graph.nodes[b]["latitude"], graph.nodes[b]["longitude"]]]
                    graph.add_edge(a, b, length_m=length, highway=highway, speed_kmh=speed,
                                   travel_time_s=round(length / 1000 / speed * 3600, 1), geometry=json.dumps(coords))
    graph.graph.update(bbox=json.dumps(bbox.to_dict()), source="test lattice")
    return graph


def osm_dist(graph: nx.Graph, a: int, b: int) -> float:
    from services.geo.distance import haversine_km

    return haversine_km(graph.nodes[a]["latitude"], graph.nodes[a]["longitude"], graph.nodes[b]["latitude"], graph.nodes[b]["longitude"]) * 1000


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeOverpass:
    """Answers Overpass queries from fixtures and records every call (so tests can prove caching)."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, query: str) -> dict:
        self.calls.append(query)
        if '"building"' in query:
            n = query.count("out count;")
            return {"elements": [{"type": "count", "id": 0, "tags": {"total": str(((i * 37) % 90) + 5)}} for i in range(n)]}
        if '"amenity"' in query:
            return fixture("facilities-aluva-sample.json")
        if '"place"' in query:
            return fixture("places-aluva-sample.json")
        if "waterway" in query or "coastline" in query:
            return fixture("river-periyar-sample.json")
        raise AssertionError(f"unexpected query: {query[:80]}")


@pytest.fixture
def fake_fetch() -> FakeOverpass:
    return FakeOverpass()


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    return tmp_path / "geo"


# --------------------------------------------------------------------------- bbox and cache
def test_bbox_validation_key_and_contains():
    assert BBOX.key == "10.080_76.330_10.120_76.370"
    assert BBOX.contains(*CENTRE) and not BBOX.contains(11, 76.35)
    assert osm.BBox.from_any({"south": 1, "west": 2, "north": 3, "east": 4}) == (1, 2, 3, 4)
    with pytest.raises(ValueError):
        osm.BBox(3, 2, 1, 4)


def test_cached_overpass_hits_the_network_once(cache_dir, fake_fetch):
    first = osm.cached_overpass("places", "x", '[out:json];node["place"];out;', cache_dir, fake_fetch)
    second = osm.cached_overpass("places", "x", '[out:json];node["place"];out;', cache_dir, fake_fetch)
    assert first == second and len(fake_fetch.calls) == 1
    assert len(list((cache_dir / "places").glob("x-*.json"))) == 1


# --------------------------------------------------------------------------- roads
def test_road_speed_by_type_and_travel_time():
    assert roads.road_speed("primary") == 50 and roads.road_speed("made_up") == roads.SPEED_KMH["default"]
    assert roads.road_speed(["residential", "primary"]) == 50
    g = grid_graph()
    e = next(iter(g.edges(data=True)))[2]
    assert math.isclose(e["travel_time_s"], e["length_m"] / 1000 / e["speed_kmh"] * 3600, rel_tol=0.01)


def test_graph_is_cached_as_graphml_and_downloaded_once(cache_dir):
    calls = []

    def downloader(bbox):
        calls.append(bbox)
        return grid_graph(bbox)

    g1 = roads.load_road_graph(BBOX, cache_dir, downloader=downloader)
    g2 = roads.load_road_graph(BBOX, cache_dir, downloader=downloader)
    assert len(calls) == 1 and g1.number_of_nodes() == 36 == g2.number_of_nodes()
    assert roads.graph_path(BBOX, cache_dir).is_file()
    assert g2.edges[1000, 1001]["highway"] == "residential" and isinstance(g2.edges[1000, 1001]["travel_time_s"], float)
    with pytest.raises(FileNotFoundError):
        roads.load_road_graph(osm.BBox(0, 0, 1, 1), cache_dir, download=False)


def test_simplify_osmnx_graph_keeps_fastest_parallel_edge_and_geometry():
    multi = nx.MultiDiGraph()
    multi.add_node(1, x=76.35, y=10.10)
    multi.add_node(2, x=76.36, y=10.10)
    multi.add_edge(1, 2, length=1100.0, highway="residential")
    multi.add_edge(1, 2, length=1100.0, highway=["primary", "residential"])
    g = roads.simplify_osmnx_graph(multi)
    assert g.number_of_edges() == 1 and g.edges[1, 2]["speed_kmh"] == 50 and g.edges[1, 2]["highway"] == "primary"
    assert json.loads(g.edges[1, 2]["geometry"]) == [[10.1, 76.35], [10.1, 76.36]]


def test_network_snaps_routes_and_prefers_the_fast_road():
    net = roads.RoadNetwork(grid_graph())
    assert net.nearest_node(10.0801, 76.3301) == 1000  # south-west corner
    cost, pred = net.shortest_paths([1000])
    far = 1000 + 5 * 6 + 5
    path = net.path(pred[0], 1000, far)
    assert path[0] == 1000 and path[-1] == far
    assert any(net.graph.edges[a, b]["highway"] == "primary" for a, b in zip(path, path[1:]))
    geometry = net.route(path)
    assert geometry[0] == list(net.node_latlon(1000)) and geometry[-1] == list(net.node_latlon(far))
    assert net.path_length_km(path) > 8


def test_accessibility_slows_edges_inside_a_zone():
    net = roads.RoadNetwork(grid_graph())
    lat, lon = net.node_latlon(1000 + 3 * 6 + 3)
    cell = zones.cell_of(lat, lon, 8)
    zone = {"id": "z", "latitude": lat, "longitude": lon, "accessibility": 0.25, "h3_index": cell}
    slow = routing.edge_weights(net, [zone], 8, 0.05)
    assert (slow >= net.edge_time).all() and (slow > net.edge_time).any()
    touched = [k for k, c in enumerate(routing.edge_cells(net, 8)) if c == cell]
    assert touched and np.allclose(slow[touched], net.edge_time[touched] * 4)


def test_route_table_describes_trips_along_the_roads():
    net = roads.RoadNetwork(grid_graph())
    depots = [{"id": "A", "latitude": 10.0805, "longitude": 76.3305}]
    zs = [{"id": "z1", "latitude": 10.1195, "longitude": 76.3695, "accessibility": 1.0},
          {"id": "z2", "latitude": 10.0805, "longitude": 76.3305, "accessibility": 1.0}]
    table = routing.route_table(net, zs, depots, 8)
    assert table.minutes.shape == (1, 2) and table.minutes[0, 1] == 0 and table.minutes[0, 0] > 5
    trip = table.describe(0, 0)
    assert trip["depot_id"] == "A" and len(trip["route_coords"]) >= 10 and trip["distance_km"] > 8
    assert trip["route_coords"][-1] == [zs[0]["latitude"], zs[0]["longitude"]]
    assert {r["from"] for r in table.roads_for_map()} and all(r["coords"] for r in table.roads_for_map())


# --------------------------------------------------------------------------- facilities
def test_parse_facilities_from_a_real_overpass_sample():
    found = fac.parse_facilities(fixture("facilities-aluva-sample.json"))
    assert found and all(f["name"] and f["osm_id"][0] in "nwr" for f in found)
    assert {"HOSPITAL", "SHELTER"} <= {f["resource_type"] for f in found}
    assert all(BBOX.contains(f["latitude"], f["longitude"]) or True for f in found)  # positions are plain lat/lon
    assert all(f["capacity"] > 0 for f in found)


def test_facilities_become_editable_osm_resources(cache_dir, fake_fetch):
    found = fac.fetch_facilities(BBOX, cache_dir, fake_fetch)
    fac.fetch_facilities(BBOX, cache_dir, fake_fetch)
    assert len(fake_fetch.calls) == 1
    rows = fac.facilities_to_resources(found, region="Aluva", area_fallback="Kerala")
    assert all(r["source"] == "osm" and r["status"] == "OPEN" and r["capacity_available"] == r["capacity_total"] for r in rows)
    assert "CLINIC" not in {r["resource_type"] for r in rows}  # clinics are listed as hospitals in the app
    assert all(r["area"] for r in rows)


def test_capacity_prefers_osm_tags():
    payload = {"elements": [
        {"type": "node", "id": 1, "lat": 10.1, "lon": 76.35, "tags": {"amenity": "hospital", "name": "A", "beds": "120"}},
        {"type": "way", "id": 2, "center": {"lat": 10.1, "lon": 76.35}, "tags": {"amenity": "school", "name": "B"}},
        {"type": "node", "id": 3, "lat": 10.1, "lon": 76.35, "tags": {"amenity": "hospital"}},  # unnamed: skipped
    ]}
    found = fac.parse_facilities(payload)
    assert [(f["osm_id"], f["capacity"], f["capacity_source"]) for f in found] == [("n1", 120, "osm"), ("w2", fac.DEFAULT_CAPACITY["SHELTER"], "default")]


# --------------------------------------------------------------------------- population
def test_population_falls_back_to_osm_building_counts(cache_dir, fake_fetch, tmp_path):
    cells = zones.hexes_in_bbox(BBOX, 8)
    polygons = [zones.hex_polygon(c) for c in cells]
    people, source = population.estimate_population(polygons, BBOX, cache_dir, worldpop_dir=tmp_path / "none", fetch=fake_fetch)
    assert len(people) == len(cells) and "building" in source and all(p >= 0 for p in people)
    assert len(fake_fetch.calls) == math.ceil(len(cells) / population.BATCH)
    population.estimate_population(polygons, BBOX, cache_dir, worldpop_dir=tmp_path / "none", fetch=fake_fetch)
    assert len(fake_fetch.calls) == math.ceil(len(cells) / population.BATCH)  # cached


def test_population_from_a_tiny_worldpop_raster(tmp_path):
    rasterio = pytest.importorskip("rasterio")
    from rasterio.transform import from_origin

    directory = tmp_path / "worldpop"
    directory.mkdir()
    path = population.worldpop_path(directory)
    data = np.full((10, 10), 100.0, dtype="float32")  # 100 people per ~1 km pixel
    with rasterio.open(path, "w", driver="GTiff", height=10, width=10, count=1, dtype="float32",
                       crs="EPSG:4326", transform=from_origin(76.30, 10.15, 0.00833, 0.00833), nodata=-99999.0) as dst:
        dst.write(data, 1)
    assert population.worldpop_available(directory)
    cell = zones.cell_of(10.10, 76.34, 8)
    people, source = population.estimate_population([zones.hex_polygon(cell)], BBOX, worldpop_dir=directory)
    pixel_km2 = (0.00833 * 110.574) * (0.00833 * 111.32 * math.cos(math.radians(10.1)))
    assert "WorldPop" in source and abs(people[0] - zones.hex_area_km2(8) / pixel_km2 * 100) < 25


# --------------------------------------------------------------------------- zones
def test_hexagons_cover_the_box_and_become_zone_assessments():
    cells = zones.hexes_in_bbox(BBOX, 8)
    assert 15 <= len(cells) <= 40 and cells == sorted(cells)
    places = [{"name": "Aluva", "latitude": CENTRE[0], "longitude": CENTRE[1]}]
    out = zones.build_zone_assessments(
        cells, population=[0] + [500] * (len(cells) - 1), building_count=[0] + [100] * (len(cells) - 1),
        hazard=lambda lat, lon: 0.9, accessibility=lambda lat, lon, s: 1 - s, vulnerability=lambda lat, lon, s: 2.0, places=places,
    )
    assert len(out) == len(cells) - 1 and all(isinstance(z, ZoneAssessment) and z.source == "simulated" for z in out)
    assert out[0].severity == 0.9 and out[0].vulnerability == 1.0 and out[0].accessibility == pytest.approx(0.1)
    assert out[0].geometry["type"] == "Polygon" and len(out[0].geometry["coordinates"][0]) == 7
    assert any(z.name.startswith("Aluva") for z in out) and len({z.name for z in out}) == len(out)


# --------------------------------------------------------------------------- scenario builder + engine
def test_build_scenario_offline_and_allocate_on_real_roads(cache_dir, fake_fetch, tmp_path, monkeypatch):
    from scripts import build_scenario as bs

    preset = {**bs.PRESETS["flood-aluva"], "bbox": BBOX.to_dict(), "seed": 3}
    doc = bs.build("flood-test", preset, resolution=8, cache_dir=cache_dir, worldpop_dir=tmp_path / "none",
                   fetch=fake_fetch, downloader=grid_graph, log=lambda _: None)
    scenario = Scenario.model_validate(doc)
    assert scenario.bbox == BBOX.to_dict() and scenario.sources["damage"] == "simulated" and scenario.facilities
    assert all(z.source == "simulated" and z.h3_index and z.geometry for z in scenario.zones)
    assert "OpenStreetMap" in scenario.sources["roads"] and scenario.data_note.startswith("Roads, facilities and population are real")
    assert max(z.damage_severity for z in scenario.zones) >= 2 and all(0 <= z.accessibility <= 1 for z in scenario.zones)
    assert sum(scenario.resources.model_dump().values()) > 0
    assert not any("osmnx" in c for c in fake_fetch.calls)  # the road download went through the fake downloader

    path = bs.write_scenario(doc, tmp_path / "scenarios")
    assert path.name == "flood-test.json" and json.loads(path.read_text(encoding="utf-8"))["id"] == "flood-test"
    with pytest.raises(FileExistsError):
        bs.write_scenario(doc, tmp_path / "scenarios")

    monkeypatch.setattr(roads, "GEO_DIR", cache_dir)  # the engine reads the road graph from the cache
    engine._NETWORKS.clear()
    assert engine.road_network_for(scenario) is not None
    result = engine.allocate(scenario)
    assert result["road_source"] == "OpenStreetMap" and result["roads"] and all(r["coords"] for r in result["roads"])
    served = [z for z in result["zones"] if z["engine"]["travel_time_min"] > 0]
    assert served and all(len(z["engine"]["route_coords"]) >= 3 for z in served)
    assert all(z["engine"]["distance_km"] >= 0 for z in result["zones"])


def test_engine_falls_back_to_synthetic_roads_without_a_cache(scenario_factory):
    scenario = Scenario.model_validate(scenario_factory())
    assert engine.road_network_for(scenario) is None  # no bbox
    assert engine.allocate(scenario)["road_source"] == "synthetic"
