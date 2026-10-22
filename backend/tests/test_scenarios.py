"""Scenario schema and loader (services/scenarios.py)."""
import json

import pytest
from pydantic import ValidationError

from services import scenarios
from services.scenarios import Scenario, ScenarioNotFoundError


def write(directory, data):
    path = directory / f"{data['id']}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_valid_scenario_parses(scenario_factory):
    scenario = Scenario.model_validate(scenario_factory())
    assert scenario.disaster_type == "flood"
    assert len(scenario.zones) == 15
    assert scenario.resources.rescue_teams == 4


@pytest.mark.parametrize(
    "field, value",
    [
        ("damage_severity", 4),
        ("damage_severity", -1),
        ("vulnerability_index", 1.2),
        ("accessibility", -0.1),
        ("population", -5),
        ("disaster_type", "volcano"),
    ],
)
def test_out_of_range_zone_values_are_rejected(scenario_factory, field, value):
    data = scenario_factory()
    data["zones"][0][field] = value
    with pytest.raises(ValidationError):
        Scenario.model_validate(data)


def test_zone_ids_must_be_unique(scenario_factory):
    data = scenario_factory()
    data["zones"][1]["id"] = data["zones"][0]["id"]
    with pytest.raises(ValidationError, match="duplicate zone id"):
        Scenario.model_validate(data)


def test_zone_disaster_type_must_match_scenario(scenario_factory):
    data = scenario_factory()
    data["zones"][0]["disaster_type"] = "earthquake"
    with pytest.raises(ValidationError, match="disaster_type"):
        Scenario.model_validate(data)


def test_missing_resource_is_rejected(scenario_factory):
    data = scenario_factory()
    del data["resources"]["shelters"]
    with pytest.raises(ValidationError):
        Scenario.model_validate(data)


def test_list_and_get_from_directory(tmp_path, scenario_factory):
    write(tmp_path, scenario_factory("b-flood"))
    write(tmp_path, scenario_factory("a-flood"))

    listed = scenarios.list_scenarios(tmp_path)
    assert [s.id for s in listed] == ["a-flood", "b-flood"]
    assert listed[0].zone_count == 15
    assert listed[0].total_population == 15 * 5000

    assert scenarios.get_scenario("b-flood", tmp_path).id == "b-flood"


def test_unknown_id_raises_not_found(tmp_path, scenario_factory):
    write(tmp_path, scenario_factory("a-flood"))
    with pytest.raises(ScenarioNotFoundError):
        scenarios.get_scenario("missing", tmp_path)


def test_path_like_ids_are_not_resolved(tmp_path, scenario_factory):
    write(tmp_path, scenario_factory("a-flood"))
    with pytest.raises(ScenarioNotFoundError):
        scenarios.get_scenario("../a-flood", tmp_path)


def test_file_id_must_match_file_name(tmp_path, scenario_factory):
    (tmp_path / "other-name.json").write_text(json.dumps(scenario_factory("a-flood")), encoding="utf-8")
    with pytest.raises(ValueError, match="other-name"):
        scenarios.get_scenario("other-name", tmp_path)
