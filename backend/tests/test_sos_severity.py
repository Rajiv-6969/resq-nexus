"""SOS severity: injuries, people affected and vulnerable people -> score and level."""
import pytest

from services.sos import severity


def test_no_details_yet_means_unknown_severity():
    assert severity(None, None, []) is None


@pytest.mark.parametrize(
    ("injuries", "people", "vulnerable", "level"),
    [
        ("none", 1, [], "Low"),
        ("none", 12, ["children", "elderly"], "Medium"),
        ("minor", 6, ["elderly"], "Medium"),
        ("serious", 1, [], "High"),
        ("minor", 25, ["children", "pregnant"], "High"),
        ("critical", 18, ["children", "elderly", "disabled"], "Critical"),
    ],
)
def test_levels_for_typical_requests(injuries, people, vulnerable, level):
    assert severity(injuries, people, vulnerable)["level"] == level


def test_a_critical_injury_is_always_critical():
    result = severity("critical", 1, [])
    assert result["level"] == "Critical"
    assert result["score"] >= 0.6


@pytest.mark.parametrize(
    ("lower", "higher"),
    [
        (("minor", 4, []), ("serious", 4, [])),
        (("minor", 2, []), ("minor", 40, [])),
        (("minor", 4, []), ("minor", 4, ["children", "elderly"])),
    ],
)
def test_worse_injuries_more_people_and_vulnerable_people_raise_the_score(lower, higher):
    assert severity(*lower)["score"] < severity(*higher)["score"]


def test_score_stays_between_0_and_1():
    groups = ["children", "elderly", "disabled", "pregnant"]
    for injuries in ("none", "minor", "serious", "critical"):
        for people in (1, 10, 50, 5000):
            score = severity(injuries, people, groups)["score"]
            assert 0 <= score <= 1


def test_unknown_or_repeated_vulnerable_groups_are_not_double_counted():
    assert severity("minor", 3, ["children", "children"]) == severity("minor", 3, ["children"])
