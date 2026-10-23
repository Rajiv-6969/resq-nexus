"""Plain-language explanations of an allocation plan (the *Explain* stage).

Zones are sent to Google Gemini in one or two batched requests (sent in
parallel). When no API key is set, or a request fails or returns something
unusable, each affected zone falls back to a template explanation built from
the same facts, so the demo never breaks.
"""
from __future__ import annotations

import json
import logging
import statistics
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from pydantic import BaseModel

from services import gemini_client
from services.scenarios import SEVERITY_LABELS

log = logging.getLogger(__name__)

BATCH_SIZE = 10  # 19 zones -> 2 requests
TIMEOUT_MS = 25_000
MAX_CHARS = 700

RESOURCE_WORDS = {
    "rescue_teams": ("rescue team", "rescue teams"),
    "medical_kits": ("medical kit", "medical kits"),
    "food_packets": ("food packet", "food packets"),
    "shelters": ("shelter unit", "shelter units"),
    "vehicles": ("vehicle", "vehicles"),
}
DAMAGE_PHRASES = {
    "flood": {1: "minor flooding", 2: "major flood damage", 3: "severe flooding that destroyed most homes"},
    "earthquake": {1: "minor earthquake damage", 2: "major earthquake damage", 3: "an earthquake that destroyed most buildings"},
    "wildfire": {1: "minor fire damage", 2: "major fire damage", 3: "a wildfire that destroyed most homes"},
}


class ZoneExplanation(BaseModel):
    """Shape Gemini is asked to return for each zone."""

    zone_id: str
    explanation: str


# --------------------------------------------------------------------------- facts
def format_count(value: int) -> str:
    """Indian digit grouping (12,34,567), matching the dashboard."""
    digits = str(int(value))
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return ",".join(([head] if head else []) + groups + [tail])


def zone_facts(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The numbers each explanation may use, one dict per zone (priority order)."""
    zones = result["zones"]
    covered = [z["engine"]["coverage_pct"] for z in zones if z["engine"]["coverage_pct"] is not None]
    average = round(statistics.mean(covered), 1) if covered else None
    depots = {d["id"]: d["name"] for d in result["depots"]}
    facts = []
    for z in zones:
        plan = z["engine"]
        facts.append({
            "zone_id": z["id"],
            "name": z["name"],
            "priority_rank": z["rank"],
            "zones_total": len(zones),
            "priority_level": z["priority_level"],
            "priority_score": z["priority_score"],
            "damage": SEVERITY_LABELS[z["damage_severity"]],
            "damage_severity": z["damage_severity"],
            "population": z["population"],
            "vulnerability_index": z["vulnerability_index"],
            "road_accessibility": z["accessibility"],
            "needs": z["demand"],
            "allocated": plan["allocated"],
            "coverage_pct": plan["coverage_pct"],
            "depot": depots.get(plan["depot_id"], plan["depot_id"]),
            "travel_time_min": plan["travel_time_min"],
            "road_distance_km": plan["distance_km"],
            "regional_average_coverage_pct": average,
            "highest_priority_first_coverage_pct": z["greedy"]["coverage_pct"],
        })
    return facts


# --------------------------------------------------------------------------- templates
def _resource_list(allocated: Mapping[str, int]) -> str:
    items = [
        f"{format_count(n)} {RESOURCE_WORDS[key][0] if n == 1 else RESOURCE_WORDS[key][1]}"
        for key, n in allocated.items() if n > 0
    ]
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def template_explanation(fact: Mapping[str, Any], disaster_type: str) -> str:
    """Two or three plain sentences built only from the zone's facts."""
    name, depot, minutes = fact["name"], fact["depot"], round(fact["travel_time_min"])
    if fact["damage_severity"] == 0:
        return (
            f"{name} reported no damage, so it needs no relief and none is sent there. "
            f"Its share goes to damaged zones instead; if that changes it can be reached from {depot} "
            f"in about {minutes} minutes by road."
        )

    damage = DAMAGE_PHRASES.get(disaster_type, {}).get(fact["damage_severity"], f"{fact['damage'].lower()} damage")
    vulnerable = ", many of them highly vulnerable" if fact["vulnerability_index"] >= 0.66 else ""
    first = (
        f"{name} is a {fact['priority_level']}-priority zone (rank {fact['priority_rank']} of {fact['zones_total']}): "
        f"{damage} affects about {format_count(fact['population'])} people{vulnerable}."
    )

    access = fact["road_accessibility"]
    roads = " over poor roads" if access < 0.3 else " over limited roads" if access < 0.6 else ""
    if not any(fact["allocated"].values()):
        return first + (
            f" The available stock runs out before its turn, so it receives nothing in this plan; "
            f"it would be served from {depot}, about {minutes} minutes away{roads}."
        )

    coverage = fact["coverage_pct"]
    second = (
        f"The Allocation Engine sends {_resource_list(fact['allocated'])} from {depot}{roads}, "
        f"about {minutes} minutes away, covering {coverage:.0f}% of its estimated needs."
    )
    average, baseline = fact["regional_average_coverage_pct"], fact["highest_priority_first_coverage_pct"]
    if baseline == 0:
        third = "A simple highest-priority-first split would have left it with nothing, so this keeps the response fair."
    elif average is not None and coverage >= average + 10:
        third = f"That is above the regional average of {average:.0f}% because its needs are among the most urgent."
    elif average is not None and coverage <= average - 10:
        third = (
            f"That is below the regional average of {average:.0f}% because scarce stock goes first to more urgent "
            f"zones, while every zone in need still gets a share."
        )
    else:
        third = f"That is close to the regional average of {average:.0f}%, keeping coverage fair across zones."
    return " ".join((first, second, third))


# --------------------------------------------------------------------------- Gemini
PROMPT = """You are an emergency-operations analyst writing a briefing for a disaster response team.
For each zone below, write 2-3 short sentences in plain English explaining why it received the relief it did.
Refer to its damage, population, vulnerability, road access, travel time from its depot and fairness
(compare its coverage with the regional average). Use only the facts given: do not invent numbers,
places or causes. Do not mention algorithms or technical methods; you may call the planner
"the Allocation Engine". Return a JSON array with one object per zone: {{"zone_id": ..., "explanation": ...}}.

Scenario: {scenario} ({disaster}, {region}).
Stock available for the whole scenario: {stock}.
Zones (JSON):
{zones}
"""


def _generate(prompt: str, model: str) -> str:
    """One Gemini request returning JSON text (isolated so tests can stub it)."""
    from google.genai import types

    response = gemini_client.get_client().models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,
            response_mime_type="application/json",
            response_schema=list[ZoneExplanation],
            http_options=types.HttpOptions(timeout=TIMEOUT_MS, retry_options=types.HttpRetryOptions(attempts=1)),
        ),
    )
    return response.text or ""


def _parse(text: str, wanted: set[str]) -> dict[str, str]:
    items = json.loads(text)
    if not isinstance(items, list):
        raise ValueError("Gemini did not return a JSON array")
    out = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        zone_id, explanation = str(item.get("zone_id", "")), item.get("explanation")
        if zone_id in wanted and isinstance(explanation, str) and explanation.strip():
            out[zone_id] = " ".join(explanation.split())[:MAX_CHARS]
    return out


def _gemini_batches(facts: Sequence[Mapping[str, Any]], context: Mapping[str, str], model: str) -> tuple[dict[str, str], list[str]]:
    """Explanations from Gemini (``zone_id -> text``) and the error type of any failed batch."""
    batches = [list(facts[i:i + BATCH_SIZE]) for i in range(0, len(facts), BATCH_SIZE)]

    def ask(batch):
        prompt = PROMPT.format(zones=json.dumps(batch, ensure_ascii=False), **context)
        return _parse(_generate(prompt, model), {f["zone_id"] for f in batch})

    texts: dict[str, str] = {}
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=len(batches) or 1) as pool:
        futures = [pool.submit(ask, batch) for batch in batches]
        for future in futures:
            try:
                texts.update(future.result())
            except Exception as exc:  # network, quota, bad JSON ... the demo must keep working
                log.warning("Gemini explanation batch failed: %s", type(exc).__name__)
                errors.append(type(exc).__name__)
    return texts, errors


def explain_allocation(result: Mapping[str, Any], region: str = "") -> dict[str, Any]:
    """Per-zone explanations for an allocation result (Gemini, with template fallback)."""
    facts = zone_facts(result)
    templates = {f["zone_id"]: template_explanation(f, result["disaster_type"]) for f in facts}
    texts: dict[str, str] = {}
    notice = None
    model = None
    if not gemini_client.is_configured():
        notice = "GEMINI_API_KEY is not set, so these explanations come from templates."
    else:
        model = gemini_client.model_name()
        context = {
            "scenario": result["scenario_name"],
            "disaster": result["disaster_type"],
            "region": region or "India",
            "stock": ", ".join(f"{format_count(v)} {RESOURCE_WORDS[k][1]}" for k, v in result["resources"].items()),
        }
        texts, errors = _gemini_batches(facts, context, model)
        missing = len(facts) - len(texts)
        if errors and not texts:
            notice = f"The Gemini request failed ({', '.join(sorted(set(errors)))}), so these explanations come from templates."
        elif missing:
            notice = f"Gemini did not explain {missing} zone(s); template text is shown for those."

    explanations = [
        {"zone_id": f["zone_id"], "text": texts.get(f["zone_id"], templates[f["zone_id"]]),
         "source": "gemini" if f["zone_id"] in texts else "template"}
        for f in facts
    ]
    sources = {e["source"] for e in explanations}
    return {
        "scenario_id": result["scenario_id"],
        "source": sources.pop() if len(sources) == 1 else "mixed",
        "model": model if texts else None,
        "notice": notice,
        "explanations": explanations,
    }
