"""Buildings -> zones: the one aggregation step shared by xBD tiles and the Indian scenarios.

Every damage source (ONNX model, xBD labels, scenario simulation) produces
``BuildingAssessment`` records; this module groups them into H3 hexagons and emits one
``ZoneAssessment`` per hexagon, which is what the Allocation Engine and the incident feed
consume. Keeping a single code path means model output and simulated input are treated
identically downstream.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any

from schemas.contracts import BuildingAssessment, Source, ZoneAssessment
from services.geo.zones import DEFAULT_RESOLUTION, cell_of, hex_centroid, hex_polygon

LOW_CONFIDENCE_THRESHOLD = 0.6  # zones whose mean model confidence is below this are flagged for field verification
DAMAGED_FROM_CLASS = 2  # major-damage and destroyed count as "damaged" (xBD convention)
CLASS_WEIGHT = {0: 0.0, 1: 1 / 3, 2: 2 / 3, 3: 1.0}


def default_accessibility(severity: float) -> float:
    """Without a road-blockage model, access degrades with damage (simulated, declared as such)."""
    return round(1.0 - 0.6 * severity, 3)


def default_vulnerability(severity: float) -> float:
    return 0.5


def aggregate_buildings(
    buildings: Iterable[BuildingAssessment],
    resolution: int = DEFAULT_RESOLUTION,
    population: Mapping[str, int] | None = None,
    names: Mapping[str, str] | None = None,
    low_confidence_threshold: float = LOW_CONFIDENCE_THRESHOLD,
    accessibility: Callable[[float], float] | Mapping[str, float] = default_accessibility,
    vulnerability: Callable[[float], float] | Mapping[str, float] = default_vulnerability,
    source: Source | None = None,
    min_buildings: int = 1,
) -> list[ZoneAssessment]:
    """One ZoneAssessment per H3 cell that contains at least ``min_buildings`` buildings.

    * ``building_count`` - buildings in the cell
    * ``damaged_pct``    - share with damage_class >= 2, in percent
    * ``severity``       - mean of damage_class / 3 (0 none ... 1 all destroyed)
    * ``mean_confidence``/``low_confidence`` - from the buildings' confidences
    * ``population``     - from ``population[cell]`` when given, else 0
    * ``source``         - the buildings' source (they must agree) unless overridden

    ``accessibility`` / ``vulnerability`` are either per-cell mappings or functions of severity.
    """
    groups: dict[str, list[BuildingAssessment]] = defaultdict(list)
    for b in buildings:
        groups[cell_of(b.lat, b.lon, resolution)].append(b)
    out: list[ZoneAssessment] = []
    for cell in sorted(groups):
        members = groups[cell]
        if len(members) < min_buildings:
            continue
        n = len(members)
        severity = sum(CLASS_WEIGHT[b.damage_class] for b in members) / n
        damaged = sum(1 for b in members if b.damage_class >= DAMAGED_FROM_CLASS) / n * 100
        confidence = sum(b.confidence for b in members) / n
        sources = {b.source for b in members}
        zone_source: Source = source or (members[0].source if len(sources) == 1 else "model")
        lat, lon = hex_centroid(cell)
        acc = accessibility[cell] if isinstance(accessibility, Mapping) else accessibility(severity)
        vul = vulnerability[cell] if isinstance(vulnerability, Mapping) else vulnerability(severity)
        out.append(ZoneAssessment(
            zone_id=cell,
            name=(names or {}).get(cell, f"Cell {cell[-6:]}"),
            geometry=hex_polygon(cell),
            centroid={"lat": lat, "lon": lon},
            building_count=n,
            damaged_pct=round(damaged, 1),
            severity=round(min(1.0, max(0.0, severity)), 3),
            population=int((population or {}).get(cell, 0)),
            vulnerability=round(min(1.0, max(0.0, float(vul))), 3),
            accessibility=round(min(1.0, max(0.0, float(acc))), 3),
            mean_confidence=round(confidence, 3),
            low_confidence=confidence < low_confidence_threshold,
            source=zone_source,
        ))
    return out


def class_counts(buildings: Iterable[BuildingAssessment]) -> dict[int, int]:
    counts = {0: 0, 1: 0, 2: 0, 3: 0}
    for b in buildings:
        counts[b.damage_class] += 1
    return counts


def severity_error(model_zones: Sequence[ZoneAssessment], label_zones: Sequence[ZoneAssessment]) -> dict[str, Any]:
    """Mean absolute difference between model- and label-based zone severity over the cells both cover."""
    labels = {z.zone_id: z.severity for z in label_zones}
    pairs = [(z.severity, labels[z.zone_id]) for z in model_zones if z.zone_id in labels]
    if not pairs:
        return {"zones": 0, "mae": None}
    return {"zones": len(pairs), "mae": round(sum(abs(a - b) for a, b in pairs) / len(pairs), 4)}
