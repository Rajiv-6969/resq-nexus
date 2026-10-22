"""Random scenario generator (generate_scenario.py)."""
import json

import pytest

import generate_scenario as gen
from services.scenarios import Scenario


def test_region_scenario_is_valid_and_has_15_to_20_zones():
    data = gen.generate_scenario("earthquake", region="kutch", seed=7)
    scenario = Scenario.model_validate(data)
    assert 15 <= len(scenario.zones) <= 20
    assert {z.disaster_type for z in scenario.zones} == {"earthquake"}
    assert scenario.synthetic is True


def test_same_seed_gives_identical_scenario():
    a = gen.generate_scenario("flood", region="assam-barpeta", seed=11)
    b = gen.generate_scenario("flood", region="assam-barpeta", seed=11)
    assert a == b


def test_different_seeds_give_different_scenarios():
    a = gen.generate_scenario("wildfire", region="kumaon", seed=1)
    b = gen.generate_scenario("wildfire", region="kumaon", seed=2)
    assert a["zones"] != b["zones"]


def test_requested_zone_count_is_used():
    data = gen.generate_scenario("wildfire", region="kumaon", seed=3, zones=15)
    assert len(data["zones"]) == 15


def test_region_without_enough_places_is_an_error():
    too_many = len(gen.load_regions()["kutch"]["places"]) + 1
    with pytest.raises(ValueError, match="places"):
        gen.generate_scenario("earthquake", region="kutch", zones=too_many)


def test_custom_centre_places_zones_inside_radius():
    centre = (19.81, 85.83)
    data = gen.generate_scenario(
        "flood", center=centre, radius_km=25, seed=5, zones=16, region_name="Puri, Odisha", state="Odisha"
    )
    scenario = Scenario.model_validate(data)
    assert len(scenario.zones) == 16
    for zone in scenario.zones:
        assert gen.distance_km(centre, (zone.latitude, zone.longitude)) <= 25.0 + 1e-6


def test_earthquake_damage_grows_towards_the_epicentre():
    # Without noise, damage depends only on distance and settlement kind, so among
    # villages the closer one is never less damaged than a farther one.
    data = gen.generate_scenario("earthquake", region="kutch", seed=1, preset_hazard=True, noise=0.0)
    kinds = {p["name"]: p["kind"] for p in gen.load_regions()["kutch"]["places"]}
    epi = (data["hazard"]["epicentre"]["latitude"], data["hazard"]["epicentre"]["longitude"])
    villages = sorted(
        (z for z in data["zones"] if kinds[z["name"]] == "village"),
        key=lambda z: gen.distance_km(epi, (z["latitude"], z["longitude"])),
    )
    severities = [z["damage_severity"] for z in villages]
    assert len(severities) >= 5
    assert severities == sorted(severities, reverse=True)
    assert severities[0] > severities[-1]


def test_preset_hazard_uses_region_defaults():
    data = gen.generate_scenario("earthquake", region="kutch", seed=9, preset_hazard=True)
    preset = gen.load_regions()["kutch"]["hazards"]["earthquake"]
    assert [data["hazard"]["epicentre"]["latitude"], data["hazard"]["epicentre"]["longitude"]] == preset["epicentre"]
    assert data["hazard"]["magnitude"] == preset["magnitude"]


def test_resources_cover_only_part_of_the_need():
    data = gen.generate_scenario("earthquake", region="kutch", seed=4, preset_hazard=True)
    need = gen.estimate_need(data["zones"])
    for key, available in data["resources"].items():
        assert available >= 1
        assert available <= need[key] or need[key] == 0


def test_cli_writes_a_valid_file_and_refuses_to_overwrite(tmp_path, capsys):
    out = tmp_path / "eq.json"
    args = ["--type", "earthquake", "--region", "kutch", "--seed", "4", "--out", str(out)]

    assert gen.main(args) == 0
    Scenario.model_validate(json.loads(out.read_text(encoding="utf-8")))

    assert gen.main(args) == 1
    assert "exists" in capsys.readouterr().err

    assert gen.main(args + ["--force"]) == 0


def test_cli_rejects_zone_counts_outside_15_to_20():
    with pytest.raises(SystemExit):
        gen.main(["--type", "flood", "--region", "assam-barpeta", "--zones", "30", "--stdout"])
