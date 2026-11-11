"""Travel times and routes between depots and zones on the real road network.

Used by the Allocation Engine: depots and zone centroids are snapped to the nearest road
node, edges inside a zone are slowed down by the zone's accessibility (0-1), and
Dijkstra's shortest path gives the time and the road geometry of every depot -> zone trip.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from services.geo.distance import haversine_km
from services.geo.roads import RoadNetwork
from services.geo.zones import DEFAULT_RESOLUTION, cell_of

MAJOR_FOR_MAP = {"motorway", "trunk", "primary", "secondary"}
UNREACHABLE_SPEED_KMH = 5.0  # straight-line fallback when a zone is off the connected network


@dataclass
class RouteTable:
    """Depot x zone travel times plus everything the API needs to describe a trip."""

    minutes: np.ndarray  # (depots, zones)
    depot_nodes: list[int]
    zone_nodes: list[int]
    depot_positions: list[tuple[float, float]]  # snapped (lat, lon) of each depot
    network: RoadNetwork
    pred: np.ndarray
    zones: Sequence[Mapping[str, Any]]
    depots: Sequence[Mapping[str, Any]]

    def describe(self, depot_index: int, zone_index: int) -> dict[str, Any]:
        """Route facts for one depot -> zone trip (along real roads)."""
        depot, zone = self.depots[depot_index], self.zones[zone_index]
        path = self.network.path(self.pred[depot_index], self.depot_nodes[depot_index], self.zone_nodes[zone_index])
        if path:
            coords = self.network.route(path)
            distance = self.network.path_length_km(path)
        else:  # off-network: straight line, slow
            coords = [list(self.depot_positions[depot_index]), [zone["latitude"], zone["longitude"]]]
            distance = haversine_km(*self.depot_positions[depot_index], zone["latitude"], zone["longitude"])
        coords.append([zone["latitude"], zone["longitude"]])  # last metres from the road to the zone centroid
        return {
            "depot_id": depot["id"],
            "route": [str(n) for n in path] or [depot["id"], zone["id"]],
            "route_coords": coords,
            "travel_time_min": round(float(self.minutes[depot_index, zone_index]), 1),
            "distance_km": round(distance, 2),
        }

    def roads_for_map(self) -> list[dict[str, Any]]:
        return self.network.major_edges(MAJOR_FOR_MAP)


def edge_cells(network: RoadNetwork, resolution: int) -> list[str]:
    """H3 cell of every edge midpoint (cached on the network object)."""
    cache = network.__dict__.setdefault("_edge_cells", {})
    if resolution not in cache:
        mid_lat = (network.lat[network.edge_u] + network.lat[network.edge_v]) / 2
        mid_lon = (network.lon[network.edge_u] + network.lon[network.edge_v]) / 2
        cache[resolution] = [cell_of(float(a), float(b), resolution) for a, b in zip(mid_lat, mid_lon)]
    return cache[resolution]


def edge_weights(network: RoadNetwork, zones: Sequence[Mapping[str, Any]], resolution: int, min_accessibility: float) -> np.ndarray:
    """Travel time per edge, divided by the accessibility of the zone the edge lies in."""
    access = {z.get("h3_index") or cell_of(z["latitude"], z["longitude"], resolution): max(float(z.get("accessibility", 1.0)), min_accessibility)
              for z in zones}
    factor = np.array([1.0 / access.get(c, 1.0) for c in edge_cells(network, resolution)], dtype=float)
    return network.edge_time * factor


def route_table(
    network: RoadNetwork,
    zones: Sequence[Mapping[str, Any]],
    depots: Sequence[Mapping[str, Any]],
    resolution: int = DEFAULT_RESOLUTION,
    min_accessibility: float = 0.05,
) -> RouteTable:
    """Snap depots and zones to the road graph and run Dijkstra from every depot."""
    zone_nodes = network.nearest_nodes((z["latitude"], z["longitude"]) for z in zones)
    depot_nodes = network.nearest_nodes((d["latitude"], d["longitude"]) for d in depots)
    weights = edge_weights(network, zones, resolution, min_accessibility)
    cost, pred = network.shortest_paths(depot_nodes, weights)
    zone_idx = [network.index[n] for n in zone_nodes]
    minutes = cost[:, zone_idx] / 60.0
    positions = [network.node_latlon(n) for n in depot_nodes]
    if not np.isfinite(minutes).all():
        for d, (lat, lon) in enumerate(positions):
            for z, zone in enumerate(zones):
                if not np.isfinite(minutes[d, z]):
                    minutes[d, z] = haversine_km(lat, lon, zone["latitude"], zone["longitude"]) / UNREACHABLE_SPEED_KMH * 60
    return RouteTable(minutes, depot_nodes, zone_nodes, positions, network, pred, zones, depots)
