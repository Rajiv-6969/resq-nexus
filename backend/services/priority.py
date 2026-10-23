"""Priority scoring: the *Prioritise* stage of Assess -> Prioritise -> Allocate -> Explain.

Each zone gets a score from 0 to about 1:

    priority = w1*severity + w2*population + w3*vulnerability + w4*(1 - accessibility)
               + equity_adjustment

Every factor is normalised to 0-1 first:

* severity       damage_severity / 3            (0 none, 1 minor, 2 major, 3 destroyed)
* population     min-max across the scenario's zones, on a log scale by default
                 (a city of 200,000 should not flatten every village to zero)
* vulnerability  vulnerability_index            (already 0-1)
* accessibility  accessibility                  (already 0-1; 1 = easy road access)

``equity_adjustment`` is a small extra boost for damaged zones with very poor road
access, so remote areas are not pushed down the list just because they are hard
to reach. It rises linearly from 0 at the accessibility threshold to ``max_boost``
at accessibility 0, which caps the score at 1 + max_boost (1.05 by default).

All tunable numbers live in ``PRIORITY_SETTINGS``; pass a modified copy to
``score_zones`` to experiment.
"""
from __future__ import annotations

import copy
import math
from collections.abc import Iterable, Mapping
from typing import Any

PRIORITY_SETTINGS: dict[str, Any] = {
    # w1..w4 from the formula; they sum to 1 so the base score stays within 0-1.
    "weights": {
        "severity": 0.40,
        "population": 0.25,
        "vulnerability": 0.20,
        "accessibility": 0.15,  # applied to (1 - accessibility)
    },
    # "log" (default) or "linear" min-max scaling of population.
    "population_scaling": "log",
    "equity": {
        "enabled": True,
        "accessibility_threshold": 0.30,  # boost only below this accessibility
        "max_boost": 0.05,  # boost at accessibility 0
        "require_damage": True,  # undamaged zones need no boost
    },
    # Minimum score for each level, checked from the top; anything lower is "Low".
    "levels": {"Critical": 0.70, "High": 0.50, "Medium": 0.30},
}

WEIGHT_KEYS = ("severity", "population", "vulnerability", "accessibility")
LEVEL_ORDER = ("Critical", "High", "Medium", "Low")


def _validate(settings: Mapping[str, Any]) -> None:
    weights = settings["weights"]
    missing = set(WEIGHT_KEYS) - set(weights)
    if missing:
        raise ValueError(f"missing weight(s): {', '.join(sorted(missing))}")
    for key in WEIGHT_KEYS:
        if weights[key] < 0:
            raise ValueError(f"weight '{key}' must not be negative")
    if settings["population_scaling"] not in ("log", "linear"):
        raise ValueError("population_scaling must be 'log' or 'linear'")
    thresholds = [settings["levels"][name] for name in LEVEL_ORDER[:-1]]
    if thresholds != sorted(thresholds, reverse=True):
        raise ValueError("level thresholds must decrease from Critical to Medium")


def normalise_severity(damage_severity: int) -> float:
    """0-3 damage scale -> 0-1."""
    return damage_severity / 3


def normalise_population(populations: list[int], scaling: str = "log") -> list[float]:
    """Min-max scale populations to 0-1 within one scenario.

    With ``"log"`` the values are log-transformed first. If every zone has the
    same population the factor cannot tell zones apart, so each gets the neutral
    midpoint 0.5 (ranking is then decided by the other factors).
    """
    values = [math.log1p(p) if scaling == "log" else float(p) for p in populations]
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


def equity_adjustment(accessibility: float, damage_severity: int, equity: Mapping[str, Any]) -> float:
    """Extra priority for damaged, hard-to-reach zones (0 when not applicable)."""
    threshold = equity["accessibility_threshold"]
    if not equity["enabled"] or accessibility >= threshold or threshold <= 0:
        return 0.0
    if equity["require_damage"] and damage_severity == 0:
        return 0.0
    return equity["max_boost"] * (threshold - accessibility) / threshold


def priority_level(score: float, levels: Mapping[str, float] | None = None) -> str:
    """Critical / High / Medium / Low from the score thresholds."""
    thresholds: Mapping[str, float] = PRIORITY_SETTINGS["levels"] if levels is None else levels
    for name in LEVEL_ORDER[:-1]:
        if score >= thresholds[name]:
            return name
    return "Low"


def score_zones(zones: Iterable[Mapping[str, Any]], settings: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """Score, rank and label zones; returns new dicts sorted by priority (highest first).

    Each result keeps the zone's own fields and adds ``priority_score``,
    ``priority_level``, ``rank``, ``factors`` (normalised 0-1 inputs) and
    ``contributions`` (weighted parts that add up to the score).
    """
    settings = settings or PRIORITY_SETTINGS
    _validate(settings)
    weights = settings["weights"]
    zones = list(zones)
    pop_norm = normalise_population([z["population"] for z in zones], settings["population_scaling"])

    scored = []
    for z, population in zip(zones, pop_norm):
        factors = {
            "severity": normalise_severity(z["damage_severity"]),
            "population": population,
            "vulnerability": float(z["vulnerability_index"]),
            "inaccessibility": 1.0 - float(z["accessibility"]),
        }
        contributions = {
            "severity": weights["severity"] * factors["severity"],
            "population": weights["population"] * factors["population"],
            "vulnerability": weights["vulnerability"] * factors["vulnerability"],
            "accessibility": weights["accessibility"] * factors["inaccessibility"],
            "equity_adjustment": equity_adjustment(z["accessibility"], z["damage_severity"], settings["equity"]),
        }
        score = round(sum(contributions.values()), 4)
        scored.append({
            **z,
            "priority_score": score,
            "priority_level": priority_level(score, settings["levels"]),
            "factors": {k: round(v, 4) for k, v in factors.items()},
            "contributions": {k: round(v, 4) for k, v in contributions.items()},
        })

    # Highest score first; ties go to worse damage, then more people, then id.
    scored.sort(key=lambda z: (-z["priority_score"], -z["damage_severity"], -z["population"], str(z["id"])))
    for rank, z in enumerate(scored, start=1):
        z["rank"] = rank
    return scored


def settings_with_weights(weights: Mapping[str, float] | None = None) -> dict[str, Any]:
    """A copy of ``PRIORITY_SETTINGS`` with custom w1..w4 rescaled to sum to 1.

    Missing weights keep their default value before rescaling; ``None`` returns
    the defaults unchanged. Rescaling keeps scores within 0-1 so the level
    thresholds stay meaningful whatever the slider positions.
    """
    settings = copy.deepcopy(PRIORITY_SETTINGS)
    if weights is None:
        return settings
    merged = {key: float(weights.get(key, settings["weights"][key])) for key in WEIGHT_KEYS}
    if any(value < 0 for value in merged.values()):
        raise ValueError("weights must not be negative")
    total = sum(merged.values())
    if total <= 0:
        raise ValueError("at least one weight must be greater than zero")
    settings["weights"] = {key: round(value / total, 6) for key, value in merged.items()}
    return settings


def level_counts(scored: Iterable[Mapping[str, Any]]) -> dict[str, int]:
    """Number of zones at each priority level (all four levels always present)."""
    counts: dict[str, int] = {level: 0 for level in LEVEL_ORDER}
    for z in scored:
        counts[z["priority_level"]] += 1
    return counts
