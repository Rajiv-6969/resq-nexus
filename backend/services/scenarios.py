"""Disaster scenarios: data model (validated with Pydantic) and file loader.

Scenario files live in ``data/scenarios/<id>.json`` at the repository root. The file name
(without ``.json``) is the scenario id used by the API.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from paths import DATA_DIR, SCENARIO_DIR  # noqa: F401  (re-exported)

DisasterType = Literal["flood", "earthquake", "wildfire", "cyclone"]
DISASTER_TYPES: tuple[str, ...] = ("flood", "earthquake", "wildfire", "cyclone")

SEVERITY_LABELS = {0: "None", 1: "Minor", 2: "Major", 3: "Destroyed"}
RESOURCE_TYPES = ("rescue_teams", "medical_kits", "food_packets", "shelters", "vehicles")


class Zone(BaseModel):
    """One affected area (village, town or ward) inside a scenario."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    disaster_type: DisasterType
    damage_severity: int = Field(ge=0, le=3, description="0 none, 1 minor, 2 major, 3 destroyed")
    population: int = Field(ge=0, description="Residents in the zone")
    vulnerability_index: float = Field(ge=0, le=1, description="0 = resilient, 1 = highly vulnerable")
    accessibility: float = Field(ge=0, le=1, description="1 = easy road access, 0 = cut off")
    h3_index: str | None = Field(None, description="H3 cell id when the zone is a hexagon")
    geometry: dict[str, Any] | None = Field(None, description="GeoJSON geometry of the zone")
    building_count: int = Field(0, ge=0, description="OpenStreetMap buildings inside the zone")
    source: str | None = Field(None, description="Where the damage values come from: model | label | simulated")


class Resources(BaseModel):
    """Relief resources available to the response team for the whole scenario."""

    model_config = ConfigDict(extra="forbid")

    rescue_teams: int = Field(ge=0, description="Search-and-rescue teams")
    medical_kits: int = Field(ge=0, description="First-aid / medical kits")
    food_packets: int = Field(ge=0, description="One-day food ration packets")
    shelters: int = Field(ge=0, description="Temporary shelter units (about 100 people each)")
    vehicles: int = Field(ge=0, description="Trucks, boats and ambulances")


class Scenario(BaseModel):
    """A complete disaster scenario: metadata, available resources and zones."""

    id: str = Field(min_length=1)
    name: str
    disaster_type: DisasterType
    region: str
    state: str
    description: str = ""
    synthetic: bool = True
    data_note: str = ""
    hazard: dict[str, Any] = Field(default_factory=dict)
    bbox: dict[str, float] | None = Field(None, description="Incident bounding box: south, west, north, east")
    geo: dict[str, Any] = Field(default_factory=dict, description="h3_resolution, road graph cache key, population source")
    sources: dict[str, str] = Field(default_factory=dict, description="Per-layer data source: roads, facilities, population, damage")
    generator: dict[str, Any] | None = None
    resources: Resources
    facilities: list[dict[str, Any]] = Field(default_factory=list, description="OpenStreetMap facilities inside bbox (seeded as editable resources)")
    zones: list[Zone] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_zones(self) -> "Scenario":
        seen: set[str] = set()
        for zone in self.zones:
            if zone.id in seen:
                raise ValueError(f"duplicate zone id '{zone.id}'")
            seen.add(zone.id)
            if zone.disaster_type != self.disaster_type:
                raise ValueError(
                    f"zone '{zone.id}' has disaster_type '{zone.disaster_type}' "
                    f"but the scenario is '{self.disaster_type}'"
                )
        return self


class ScenarioSummary(BaseModel):
    """Short listing entry for GET /scenarios."""

    id: str
    name: str
    disaster_type: DisasterType
    region: str
    state: str
    zone_count: int
    total_population: int
    synthetic: bool


class ScenarioNotFoundError(LookupError):
    """No scenario file with the requested id."""


def _scenario_files(directory: Path) -> dict[str, Path]:
    # Ids come only from files that exist, so a request can never resolve
    # a path outside the scenario folder.
    return {path.stem: path for path in sorted(Path(directory).glob("*.json"))}


def _load(path: Path) -> Scenario:
    data = json.loads(path.read_text(encoding="utf-8"))
    scenario = Scenario.model_validate(data)
    if scenario.id != path.stem:
        raise ValueError(f"{path.name}: id '{scenario.id}' does not match file name '{path.stem}'")
    return scenario


def list_scenarios(directory: Path = SCENARIO_DIR) -> list[ScenarioSummary]:
    """Summaries of every scenario in ``directory``, sorted by id."""
    summaries = []
    for path in _scenario_files(directory).values():
        s = _load(path)
        summaries.append(
            ScenarioSummary(
                id=s.id,
                name=s.name,
                disaster_type=s.disaster_type,
                region=s.region,
                state=s.state,
                zone_count=len(s.zones),
                total_population=sum(z.population for z in s.zones),
                synthetic=s.synthetic,
            )
        )
    return summaries


def get_scenario(scenario_id: str, directory: Path = SCENARIO_DIR) -> Scenario:
    """Load one scenario by id; raises ScenarioNotFoundError if there is no such file."""
    path = _scenario_files(directory).get(scenario_id)
    if path is None:
        raise ScenarioNotFoundError(scenario_id)
    return _load(path)
