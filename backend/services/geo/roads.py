"""OpenStreetMap road network for an incident bounding box.

``load_road_graph`` returns an undirected NetworkX graph whose nodes are OSM nodes
(``latitude`` / ``longitude``) and whose edges carry ``length_m``, ``highway``,
``speed_kmh``, ``travel_time_s`` and the road ``geometry`` (JSON list of [lat, lon]).
The graph is downloaded once with OSMnx and cached as gzipped GraphML under
``data/geo/roads/<bbox key>.graphml.gz``; afterwards only NetworkX is needed.

``RoadNetwork`` wraps a graph for the Allocation Engine: nearest-node snapping (KD-tree
on a local kilometre grid), Dijkstra from many sources (SciPy, C speed) and route
geometry along the real roads.
"""
from __future__ import annotations

import gzip
import json
import math
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.spatial import cKDTree

from services.geo.osm import GEO_DIR, OVERPASS_MIRRORS, BBox

# Typical free-flow speed per OSM ``highway`` value (km/h). Unknown types use ``default``.
SPEED_KMH: dict[str, float] = {
    "motorway": 80, "motorway_link": 50, "trunk": 60, "trunk_link": 40,
    "primary": 50, "primary_link": 35, "secondary": 40, "secondary_link": 30,
    "tertiary": 30, "tertiary_link": 25, "unclassified": 25, "residential": 20,
    "living_street": 10, "service": 15, "road": 25, "track": 10,
    "path": 4, "footway": 4, "pedestrian": 4, "bridleway": 5, "steps": 2, "cycleway": 12,  # network_type="all" (hill areas)
    "default": 25,
}
MAJOR_ROADS = {"motorway", "trunk", "primary", "secondary", "tertiary"}


def road_speed(highway: Any) -> float:
    """Speed for an OSM highway tag (a list of tags uses the fastest one)."""
    tags = highway if isinstance(highway, (list, tuple)) else [highway]
    return max((SPEED_KMH.get(str(t), SPEED_KMH["default"]) for t in tags), default=SPEED_KMH["default"])


def graph_path(bbox: BBox, cache_dir: Path | None = None) -> Path:
    return (cache_dir or GEO_DIR) / "roads" / f"{bbox.key}.graphml.gz"


def _first(value: Any) -> Any:
    return value[0] if isinstance(value, (list, tuple)) and value else value


def simplify_osmnx_graph(multi: Any) -> nx.Graph:
    """Collapse an OSMnx MultiDiGraph into the flat undirected graph described above."""
    graph = nx.Graph()
    for node, data in multi.nodes(data=True):
        graph.add_node(int(node), latitude=round(float(data["y"]), 6), longitude=round(float(data["x"]), 6))
    for u, v, data in multi.edges(data=True):
        u, v = int(u), int(v)
        if u == v:
            continue
        length = float(data.get("length", 0.0))
        highway = _first(data.get("highway", "unclassified"))
        speed = road_speed(data.get("highway", highway))
        travel = length / 1000.0 / speed * 3600.0
        if graph.has_edge(u, v) and graph.edges[u, v]["travel_time_s"] <= travel:
            continue
        geometry = data.get("geometry")
        if geometry is not None and hasattr(geometry, "coords"):
            coords = [[round(y, 6), round(x, 6)] for x, y in geometry.coords]
            if coords and coords[0] != [graph.nodes[u]["latitude"], graph.nodes[u]["longitude"]]:
                coords.reverse()
        else:
            coords = [[graph.nodes[u]["latitude"], graph.nodes[u]["longitude"]], [graph.nodes[v]["latitude"], graph.nodes[v]["longitude"]]]
        graph.add_edge(u, v, length_m=round(length, 1), highway=str(highway), speed_kmh=float(speed),
                       travel_time_s=round(travel, 1), geometry=json.dumps(coords, separators=(",", ":")))
    return graph


def download_graph(bbox: BBox, network_type: str = "drive", retain_all: bool = False) -> nx.Graph:
    """Download the road network inside ``bbox`` with OSMnx (network).

    ``network_type`` is OSMnx's: ``drive`` for towns, ``all`` where relief moves on tracks and
    paths (hill districts). ``retain_all=True`` keeps disconnected pieces of the network.
    """
    import osmnx as ox  # heavy optional dependency: only needed to build the cache

    ox.settings.use_cache = False  # our GraphML cache is the only one we keep
    ox.settings.requests_timeout = 300
    ox.settings.overpass_rate_limit = False  # the /api/status pause can sleep for hours on a busy mirror; we retry instead
    ox.settings.log_console = True
    ox.settings.max_query_area_size = 25_000_000  # m2: split dense city boxes into ~25 km2 requests the public servers can serve
    last: Exception | None = None
    for attempt in range(5):
        if attempt:
            time.sleep(30 * 2 ** (attempt - 1))  # the public servers ask for exponential backoff
        for mirror in OVERPASS_MIRRORS:
            ox.settings.overpass_url = mirror.removesuffix("/interpreter")
            try:
                multi = ox.graph_from_bbox((bbox.west, bbox.south, bbox.east, bbox.north), network_type=network_type,
                                           simplify=True, retain_all=retain_all, truncate_by_edge=True)
                break
            except Exception as exc:  # noqa: BLE001 - timeouts, 429/504 from a busy mirror
                last = exc
                print(f"  download attempt {attempt + 1} via {mirror} failed: {type(exc).__name__}: {str(exc)[:160]}", file=sys.stderr)
        else:
            continue
        break
    else:
        raise RuntimeError(f"OSMnx download failed after 5 attempts: {last}") from last
    graph = simplify_osmnx_graph(multi)
    graph.graph.update(bbox=json.dumps(bbox.to_dict()), source="OpenStreetMap (OSMnx)", network_type=network_type)
    return graph


def save_graph(graph: nx.Graph, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    with gzip.open(partial, "wb") as handle:
        nx.write_graphml(graph, handle)
    partial.replace(path)
    return path


def read_graph(path: Path) -> nx.Graph:
    with gzip.open(path, "rb") as handle:
        return nx.read_graphml(handle, node_type=int)


_MEMORY: dict[tuple[str, float], nx.Graph] = {}


def load_road_graph(bbox: Any, cache_dir: Path | None = None, download: bool = True,
                    downloader: Callable[[BBox], nx.Graph] = download_graph) -> nx.Graph:
    """The road graph for ``bbox`` from the cache, downloading and caching it if allowed."""
    bbox = BBox.from_any(bbox)
    path = graph_path(bbox, cache_dir)
    if path.is_file():
        key = (str(path), path.stat().st_mtime)
        if key not in _MEMORY:
            _MEMORY.clear()
            _MEMORY[key] = read_graph(path)
        return _MEMORY[key]
    if not download:
        raise FileNotFoundError(f"no cached road graph at {path}; run build_scenario.py with network access")
    graph = downloader(bbox)
    save_graph(graph, path)
    return load_road_graph(bbox, cache_dir, download=False)


def edge_geometry(graph: nx.Graph, u: int, v: int) -> list[list[float]]:
    """[lat, lon] points of the edge u-v, ordered from u to v."""
    coords = json.loads(graph.edges[u, v]["geometry"])
    start = [graph.nodes[u]["latitude"], graph.nodes[u]["longitude"]]
    if coords and math.dist(coords[0], start) > math.dist(coords[-1], start):
        coords.reverse()
    return coords


def route_geometry(graph: nx.Graph, path: Sequence[int]) -> list[list[float]]:
    """Concatenated road geometry of a node path (duplicate joins removed)."""
    if len(path) < 2:
        return [[graph.nodes[n]["latitude"], graph.nodes[n]["longitude"]] for n in path]
    out: list[list[float]] = []
    for a, b in zip(path, path[1:]):
        for point in edge_geometry(graph, a, b):
            if not out or out[-1] != point:
                out.append(point)
    return out


class RoadNetwork:
    """Array view of a road graph: snapping, many-source Dijkstra and route geometry."""

    def __init__(self, graph: nx.Graph) -> None:
        self.graph = graph
        self.nodes: list[int] = list(graph.nodes)
        self.index = {n: i for i, n in enumerate(self.nodes)}
        self.lat = np.array([graph.nodes[n]["latitude"] for n in self.nodes], dtype=float)
        self.lon = np.array([graph.nodes[n]["longitude"] for n in self.nodes], dtype=float)
        lat0 = float(self.lat.mean()) if self.nodes else 0.0
        self._kx, self._ky = 111.320 * math.cos(math.radians(lat0)), 110.574
        self._tree = cKDTree(np.column_stack((self.lon * self._kx, self.lat * self._ky))) if self.nodes else None
        edges = list(graph.edges(data=True))
        self.edge_u = np.array([self.index[u] for u, _, _ in edges], dtype=np.int64)
        self.edge_v = np.array([self.index[v] for _, v, _ in edges], dtype=np.int64)
        self.edge_time = np.array([float(d["travel_time_s"]) for _, _, d in edges], dtype=float)
        self.edge_length = np.array([float(d["length_m"]) for _, _, d in edges], dtype=float)
        self.edge_highway = [str(d.get("highway", "")) for _, _, d in edges]

    def __len__(self) -> int:
        return len(self.nodes)

    def nearest_node(self, lat: float, lon: float) -> int:
        """OSM node id of the road node closest to (lat, lon)."""
        if self._tree is None:
            raise ValueError("empty road network")
        _, i = self._tree.query([lon * self._kx, lat * self._ky])
        return self.nodes[int(i)]

    def nearest_nodes(self, points: Iterable[tuple[float, float]]) -> list[int]:
        return [self.nearest_node(lat, lon) for lat, lon in points]

    def node_latlon(self, node: int) -> tuple[float, float]:
        i = self.index[node]
        return float(self.lat[i]), float(self.lon[i])

    def edge_endpoints_latlon(self) -> np.ndarray:
        """(edges, 2, 2) array of [lat, lon] for both ends of every edge."""
        return np.stack((np.column_stack((self.lat[self.edge_u], self.lon[self.edge_u])),
                         np.column_stack((self.lat[self.edge_v], self.lon[self.edge_v]))), axis=1)

    def matrix(self, weights: np.ndarray | None = None):
        """Symmetric sparse adjacency matrix weighted by ``weights`` (default: travel time in seconds)."""
        w = self.edge_time if weights is None else np.asarray(weights, dtype=float)
        n = len(self.nodes)
        rows = np.concatenate((self.edge_u, self.edge_v))
        cols = np.concatenate((self.edge_v, self.edge_u))
        return coo_matrix((np.concatenate((w, w)), (rows, cols)), shape=(n, n)).tocsr()

    def shortest_paths(self, sources: Sequence[int], weights: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
        """Dijkstra from each source node: ``(cost[source, node], predecessor[source, node])``."""
        src = [self.index[s] for s in sources]
        cost, pred = dijkstra(self.matrix(weights), directed=False, indices=src, return_predecessors=True)
        return cost, pred

    def path(self, pred_row: np.ndarray, source: int, target: int) -> list[int]:
        """Node ids from ``source`` to ``target`` using one row of the predecessor matrix."""
        i, s = self.index[target], self.index[source]
        if i != s and pred_row[i] < 0:
            return []
        out = [i]
        while out[-1] != s:
            out.append(int(pred_row[out[-1]]))
        return [self.nodes[j] for j in reversed(out)]

    def path_length_km(self, path: Sequence[int]) -> float:
        return sum(float(self.graph.edges[a, b]["length_m"]) for a, b in zip(path, path[1:])) / 1000.0

    def route(self, path: Sequence[int]) -> list[list[float]]:
        return route_geometry(self.graph, path)

    def major_edges(self, kinds: set[str] = MAJOR_ROADS) -> list[dict[str, Any]]:
        """Trunk/primary/secondary/tertiary roads with geometry, for the map's road layer."""
        out = []
        for k, (u, v) in enumerate(zip(self.edge_u, self.edge_v)):
            if self.edge_highway[k] in kinds:
                a, b = self.nodes[u], self.nodes[v]
                out.append({"from": str(a), "to": str(b), "distance_km": round(self.edge_length[k] / 1000, 3),
                            "travel_time_min": round(self.edge_time[k] / 60, 1), "coords": edge_geometry(self.graph, a, b)})
        return out
