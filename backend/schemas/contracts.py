"""Shared contracts between ml/ (assessment) and the backend (prioritise, allocate).

These are the only shapes the two sides exchange:

* ``BuildingAssessment`` - one building and its damage class.
* ``ZoneAssessment``     - one zone (ward / village / grid cell) with aggregated damage,
                           population, vulnerability, road access and live SOS demand.
* The allocation request / result shapes keep the API's existing form
  (``AllocationRequest`` / ``AllocationResponse`` in main.py); the Allocation Engine
  accepts either a ``Scenario`` or a list of ``ZoneAssessment``.

Every record says where it came from (``source``) so the UI can state what is real and
what is simulated. ``damage_class`` / ``damage_severity`` scale: 0 none, 1 minor,
2 major, 3 destroyed (the xBD scale).
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Source = Literal["model", "label", "simulated"]
DamageClass = Literal[0, 1, 2, 3]
DAMAGE_CLASS_LABELS = {0: "none", 1: "minor", 2: "major", 3: "destroyed"}


class BuildingAssessment(BaseModel):
    """Damage class of one building footprint."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    damage_class: DamageClass = Field(description="0 none, 1 minor, 2 major, 3 destroyed")
    confidence: float = Field(ge=0, le=1, description="Model confidence in the class, 0-1")
    source: Source


class Centroid(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class ZoneAssessment(BaseModel):
    """Aggregated damage and need of one zone - the Allocation Engine's unit of work."""

    model_config = ConfigDict(extra="forbid")

    zone_id: str = Field(min_length=1)
    name: str = ""
    geometry: dict[str, Any] | None = Field(None, description="GeoJSON geometry of the zone (Polygon/MultiPolygon)")
    centroid: Centroid
    building_count: int = Field(0, ge=0)
    damaged_pct: float = Field(0, ge=0, le=100, description="Share of buildings with damage_class >= 2")
    severity: float = Field(ge=0, le=1, description="0 none ... 1 destroyed")
    population: int = Field(ge=0)
    vulnerability: float = Field(ge=0, le=1, description="0 resilient ... 1 highly vulnerable")
    accessibility: float = Field(ge=0, le=1, description="1 easy road access ... 0 cut off")
    mean_confidence: float = Field(1.0, ge=0, le=1)
    low_confidence: bool = False
    sos_demand: dict[str, int] = Field(default_factory=dict, description="Extra units per resource from live SOS requests")
    source: Source

    @property
    def damage_severity(self) -> int:
        """Nearest 0-3 damage class for the existing priority and demand models."""
        return max(0, min(3, round(self.severity * 3)))

    def to_zone_dict(self, disaster_type: str = "flood") -> dict[str, Any]:
        """The flat zone dict used by services.priority and the Allocation Engine."""
        return {
            "id": self.zone_id,
            "name": self.name or self.zone_id,
            "latitude": self.centroid.lat,
            "longitude": self.centroid.lon,
            "disaster_type": disaster_type,
            "damage_severity": self.damage_severity,
            "population": self.population,
            "vulnerability_index": self.vulnerability,
            "accessibility": self.accessibility,
        }


def zone_assessment_from_zone(zone: Any, source: Source = "simulated", **extra: Any) -> ZoneAssessment:
    """Build a ZoneAssessment from a scenario Zone (pydantic model or dict)."""
    z = zone if isinstance(zone, dict) else zone.model_dump()
    fields = {
        "zone_id": z["id"],
        "name": z["name"],
        "centroid": {"lat": z["latitude"], "lon": z["longitude"]},
        "severity": z["damage_severity"] / 3,
        "population": z["population"],
        "vulnerability": z["vulnerability_index"],
        "accessibility": z["accessibility"],
        "source": source,
    }
    fields.update(extra)
    return ZoneAssessment.model_validate(fields)
