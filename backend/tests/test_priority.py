"""Priority scoring (services/priority.py)."""
import copy
import math

import pytest

from services import priority
from services.priority import PRIORITY_SETTINGS, score_zones


def zone(zone_id="Z1", severity=2, population=1000, vulnerability=0.5, accessibility=0.5):
    return {
        "id": zone_id,
        "name": zone_id,
        "latitude": 26.0,
        "longitude": 91.0,
        "disaster_type": "flood",
        "damage_severity": severity,
        "population": population,
        "vulnerability_index": vulnerability,
        "accessibility": accessibility,
    }


def settings(**changes):
    """Copy of the default settings with top-level keys replaced."""
    s = copy.deepcopy(PRIORITY_SETTINGS)
    s.update(changes)
    return s


NO_EQUITY = {"enabled": False, "accessibility_threshold": 0.3, "max_boost": 0.05, "require_damage": True}


# ---------------------------------------------------------------- settings
def test_default_weights_match_the_specification():
    assert PRIORITY_SETTINGS["weights"] == {
        "severity": 0.40,
        "population": 0.25,
        "vulnerability": 0.20,
        "accessibility": 0.15,
    }


def test_negative_weight_is_rejected():
    bad = settings(weights={"severity": -0.1, "population": 0.5, "vulnerability": 0.3, "accessibility": 0.3})
    with pytest.raises(ValueError, match="weight"):
        score_zones([zone()], bad)


# ---------------------------------------------------------------- normalisation
def test_severity_is_scaled_from_0_to_3_onto_0_to_1():
    assert [priority.normalise_severity(s) for s in (0, 1, 2, 3)] == pytest.approx([0, 1 / 3, 2 / 3, 1])


def test_log_population_scaling_spans_0_to_1():
    norm = priority.normalise_population([100, 1000, 10000], "log")
    assert norm[0] == pytest.approx(0.0)
    assert norm[2] == pytest.approx(1.0)
    assert norm[1] == pytest.approx(0.5, abs=0.01)  # 1000 is half-way between 100 and 10000 on a log scale


def test_linear_population_scaling_is_min_max():
    assert priority.normalise_population([0, 50, 100], "linear") == pytest.approx([0.0, 0.5, 1.0])


def test_equal_populations_get_a_neutral_value():
    assert priority.normalise_population([500, 500, 500], "log") == [0.5, 0.5, 0.5]


# ---------------------------------------------------------------- the formula
def test_score_matches_the_formula_by_hand():
    zones = [
        zone("A", severity=3, population=10000, vulnerability=0.8, accessibility=0.2),
        zone("B", severity=1, population=100, vulnerability=0.4, accessibility=0.9),
    ]
    result = {z["id"]: z for z in score_zones(zones, settings(equity=NO_EQUITY))}
    # A: 0.4*1 + 0.25*1 + 0.2*0.8 + 0.15*(1-0.2) = 0.93
    assert result["A"]["priority_score"] == pytest.approx(0.93, abs=1e-4)
    # B: 0.4*(1/3) + 0.25*0 + 0.2*0.4 + 0.15*(1-0.9) = 0.228333
    assert result["B"]["priority_score"] == pytest.approx(0.2283, abs=1e-4)


def test_contributions_add_up_to_the_score():
    zones = [zone("A", 3, 5000, 0.7, 0.1), zone("B", 0, 200, 0.2, 0.9), zone("C", 2, 900, 0.5, 0.5)]
    for z in score_zones(zones):
        assert sum(z["contributions"].values()) == pytest.approx(z["priority_score"], abs=1e-3)


def test_custom_weights_come_from_the_settings_dict():
    only_severity = settings(
        weights={"severity": 1.0, "population": 0.0, "vulnerability": 0.0, "accessibility": 0.0},
        equity=NO_EQUITY,
    )
    result = score_zones([zone("A", severity=2, accessibility=0.0), zone("B", severity=0)], only_severity)
    assert [z["priority_score"] for z in result] == pytest.approx([2 / 3, 0.0], abs=1e-4)


@pytest.mark.parametrize(
    "field, low, high",
    [("severity", 1, 3), ("vulnerability", 0.2, 0.9), ("population", 500, 50000)],
)
def test_more_of_a_risk_factor_means_higher_priority(field, low, high):
    reference = zone("REF", population=100)  # anchors the population range
    a = zone("LOW", **{field: low})
    b = zone("HIGH", **{field: high})
    if field == "population":
        reference = zone("REF", population=200000)
    scores = {z["id"]: z["priority_score"] for z in score_zones([reference, a, b])}
    assert scores["HIGH"] > scores["LOW"]


def test_poor_access_means_higher_priority():
    scores = {z["id"]: z["priority_score"] for z in score_zones([zone("EASY", accessibility=0.9), zone("HARD", accessibility=0.4)])}
    assert scores["HARD"] > scores["EASY"]


# ---------------------------------------------------------------- equity adjustment
def test_equity_boost_applies_only_to_damaged_low_access_zones():
    equity = PRIORITY_SETTINGS["equity"]
    assert priority.equity_adjustment(0.10, 2, equity) > 0
    assert priority.equity_adjustment(0.00, 2, equity) == pytest.approx(equity["max_boost"])
    assert priority.equity_adjustment(0.50, 2, equity) == 0  # accessible
    assert priority.equity_adjustment(0.10, 0, equity) == 0  # remote but undamaged


def test_equity_boost_lifts_remote_zone_above_plain_formula():
    remote = zone("REMOTE", accessibility=0.05)
    with_equity = score_zones([remote])[0]["priority_score"]
    without = score_zones([remote], settings(equity=NO_EQUITY))[0]["priority_score"]
    assert with_equity > without
    assert with_equity - without <= PRIORITY_SETTINGS["equity"]["max_boost"] + 1e-9


# ---------------------------------------------------------------- ranking and levels
def test_zones_are_sorted_and_ranked():
    zones = [zone("LOW", 0, 100, 0.1, 0.9), zone("TOP", 3, 9000, 0.9, 0.1), zone("MID", 2, 2000, 0.5, 0.5)]
    result = score_zones(zones)
    assert [z["id"] for z in result] == ["TOP", "MID", "LOW"]
    assert [z["rank"] for z in result] == [1, 2, 3]
    scores = [z["priority_score"] for z in result]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.parametrize(
    "score, level",
    [(0.95, "Critical"), (0.70, "Critical"), (0.6999, "High"), (0.50, "High"),
     (0.4999, "Medium"), (0.30, "Medium"), (0.2999, "Low"), (0.0, "Low")],
)
def test_priority_level_thresholds(score, level):
    assert priority.priority_level(score) == level


def test_scored_zone_keeps_original_fields():
    result = score_zones([zone("A")])[0]
    assert result["name"] == "A" and result["population"] == 1000
    assert set(result["factors"]) == {"severity", "population", "vulnerability", "inaccessibility"}
    assert not math.isnan(result["priority_score"])
