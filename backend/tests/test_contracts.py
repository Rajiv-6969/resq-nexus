"""schemas/contracts.py: shared assessment shapes and the Allocation Engine accepting them."""
import pytest
from pydantic import ValidationError

from schemas.contracts import BuildingAssessment, ZoneAssessment, zone_assessment_from_zone
from services import allocation_engine as engine
from services.scenarios import Scenario, get_scenario


def test_building_assessment_validates_scale():
    b = BuildingAssessment(id="b1", lat=26.1, lon=91.7, damage_class=3, confidence=0.9, source="model")
    assert b.damage_class == 3
    with pytest.raises(ValidationError):
        BuildingAssessment(id="b1", lat=26.1, lon=91.7, damage_class=4, confidence=0.9, source="model")
    with pytest.raises(ValidationError):
        BuildingAssessment(id="b1", lat=26.1, lon=91.7, damage_class=1, confidence=1.2, source="model")
    with pytest.raises(ValidationError):
        BuildingAssessment(id="b1", lat=26.1, lon=91.7, damage_class=1, confidence=0.5, source="guess")


def test_zone_assessment_round_trip_from_zone():
    zone = get_scenario("flood-assam").zones[0]
    za = zone_assessment_from_zone(zone, source="label")
    assert za.zone_id == zone.id and za.source == "label"
    assert za.damage_severity == zone.damage_severity
    assert za.to_zone_dict("flood")["population"] == zone.population


def test_engine_accepts_zone_assessments(scenario_factory):
    scenario = Scenario.model_validate(scenario_factory())
    assessments = [zone_assessment_from_zone(z) for z in scenario.zones]
    assessments[0].sos_demand = {"rescue_teams": 2}
    result = engine.allocate(assessments, resources=scenario.resources, disaster_type="flood")
    assert {z["id"] for z in result["zones"]} == {z.id for z in scenario.zones}
    first = next(z for z in result["zones"] if z["id"] == assessments[0].zone_id)
    plain = engine.allocate(scenario)
    plain_first = next(z for z in plain["zones"] if z["id"] == assessments[0].zone_id)
    assert first["demand"]["rescue_teams"] == plain_first["demand"]["rescue_teams"] + 2


def test_engine_requires_stock_for_assessments(scenario_factory):
    scenario = Scenario.model_validate(scenario_factory())
    with pytest.raises(ValueError):
        engine.allocate([zone_assessment_from_zone(z) for z in scenario.zones])
