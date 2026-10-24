"""SOS requests: severity score, the status workflow and the JSON shape the API returns."""
from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from db.models import SosRequest
from services.geo import haversine_km
from services.resources import serialize as serialize_resource

# Severity = 0.5 x injuries + 0.3 x people affected + 0.2 x vulnerable groups (each 0-1).
INJURY_SCORE = {"none": 0.0, "minor": 0.35, "serious": 0.7, "critical": 1.0}
SEVERITY_WEIGHTS = {"injuries": 0.5, "people": 0.3, "vulnerable": 0.2}
PEOPLE_AT_FULL_SCORE = 50  # people score = ln(1 + people) / ln(1 + 50), capped at 1
VULNERABLE_GROUPS = ("children", "elderly", "disabled", "pregnant")
CRITICAL_INJURY_FLOOR = 0.60  # a critical injury always rates Critical
LEVELS = (("Critical", 0.60), ("High", 0.40), ("Medium", 0.20))

EMERGENCY_TYPES = ("flood", "earthquake", "wildfire", "cyclone", "fire", "medical", "other")
NEEDS = ("rescue", "medical", "ambulance", "food", "water", "shelter")

STATUS_FLOW = ("PENDING", "ACKNOWLEDGED", "DISPATCHED", "RESOLVED")
ACTIVE_STATUSES = STATUS_FLOW[:-1]
_STAMP = {"PENDING": "created_at", "ACKNOWLEDGED": "acknowledged_at", "DISPATCHED": "dispatched_at", "RESOLVED": "resolved_at"}


def severity(injuries: str | None, people_affected: int | None, vulnerable: Iterable[str]) -> dict[str, Any] | None:
    """Score (0-1) and level of one request; None until its details are known."""
    if injuries is None or people_affected is None:
        return None
    people = min(1.0, math.log1p(people_affected) / math.log1p(PEOPLE_AT_FULL_SCORE))
    groups = len(set(vulnerable) & set(VULNERABLE_GROUPS)) / len(VULNERABLE_GROUPS)
    score = (SEVERITY_WEIGHTS["injuries"] * INJURY_SCORE[injuries]
             + SEVERITY_WEIGHTS["people"] * people
             + SEVERITY_WEIGHTS["vulnerable"] * groups)
    if injuries == "critical":
        score = max(score, CRITICAL_INJURY_FLOOR)
    score = round(min(score, 1.0), 3)
    level = next((name for name, floor in LEVELS if score >= floor), "Low")
    return {"score": score, "level": level}


def sos_severity(sos: SosRequest) -> dict[str, Any] | None:
    return severity(sos.injuries, sos.people_affected, sos.vulnerable or [])


def next_status(status: str) -> str | None:
    index = STATUS_FLOW.index(status)
    return STATUS_FLOW[index + 1] if index + 1 < len(STATUS_FLOW) else None


class TransitionError(ValueError):
    """The requested status change is not allowed from the request's current status (HTTP 409)."""


def accept(sos: SosRequest, provider_id: int, now: datetime) -> None:
    """A provider takes on a PENDING request (unassigned, or assigned to them by an admin)."""
    if sos.status != "PENDING":
        if sos.assigned_provider_id == provider_id:
            raise TransitionError("You have already accepted this request.")
        raise TransitionError("This request has already been accepted by another provider.")
    if sos.assigned_provider_id not in (None, provider_id):
        raise TransitionError("This request is assigned to another provider.")
    if sos.assigned_provider_id is None:
        sos.assigned_provider_id = provider_id
        sos.assigned_at = now
    sos.status = "ACKNOWLEDGED"
    sos.acknowledged_at = sos.updated_at = now


def advance(sos: SosRequest, target: str, now: datetime) -> None:
    """Move a request to the next status in PENDING -> ACKNOWLEDGED -> DISPATCHED -> RESOLVED."""
    if sos.status == "RESOLVED":
        raise TransitionError("This request is already resolved.")
    expected = next_status(sos.status)
    if target != expected:
        raise TransitionError(f"This request is {sos.status}; move it to {expected} first.")
    setattr(sos, _STAMP[target], now)
    sos.status = target
    sos.updated_at = now


def resolve(sos: SosRequest, now: datetime) -> None:
    """Close an active request straight away (admins, e.g. a duplicate or a false alarm)."""
    if sos.status == "RESOLVED":
        raise TransitionError("This request is already resolved.")
    sos.status = "RESOLVED"
    sos.resolved_at = sos.updated_at = now


# --------------------------------------------------------------------------- provider suggestions
# Resource types that can meet each need, best match first.
NEED_RESOURCE_TYPES = {
    "rescue": ("FIRE_STATION", "POLICE"),
    "medical": ("HOSPITAL", "AMBULANCE"),
    "ambulance": ("AMBULANCE", "HOSPITAL"),
    "food": ("FOOD", "SHELTER"),
    "water": ("WATER", "FOOD"),
    "shelter": ("SHELTER",),
}
# Needs assumed from the emergency type when a request lists none.
EMERGENCY_NEEDS = {
    "flood": ("rescue", "shelter"),
    "earthquake": ("rescue", "medical"),
    "wildfire": ("rescue",),
    "cyclone": ("shelter", "rescue"),
    "fire": ("rescue",),
    "medical": ("medical", "ambulance"),
    "other": (),
}
SUGGESTION_RADIUS_KM = 75
SUGGESTION_LIMIT = 5


def needs_for(sos: SosRequest) -> list[str]:
    """The needs a provider should meet: the citizen's own list, else what the emergency type implies."""
    if sos.needs:
        return [need for need in NEEDS if need in sos.needs]
    return list(EMERGENCY_NEEDS.get(sos.emergency_type or "", ()))


def suggest_providers(sos: SosRequest, providers: Iterable, limit: int = SUGGESTION_LIMIT) -> list[dict[str, Any]]:
    """Approved providers that can help, nearest first: each with its closest suitable resource that is
    OPEN with capacity left. A request without needs yet considers every resource type."""
    needs = needs_for(sos)
    wanted = {t for need in needs for t in NEED_RESOURCE_TYPES[need]} or None
    candidates = []
    for provider in providers:
        if provider.approval_status != "APPROVED" or not provider.user.is_active:
            continue
        usable = [
            (haversine_km(sos.latitude, sos.longitude, r.latitude, r.longitude), r)
            for r in provider.resources
            if r.status == "OPEN" and r.capacity_available > 0 and (wanted is None or r.resource_type in wanted)
        ]
        if not usable:
            continue
        distance, resource = min(usable, key=lambda pair: (pair[0], pair[1].name))
        if distance > SUGGESTION_RADIUS_KM:
            continue
        candidates.append({
            "provider": provider_brief(provider),
            "resource": serialize_resource(resource, distance),
            "distance_km": round(distance, 2),
            "matched_needs": [need for need in needs if resource.resource_type in NEED_RESOURCE_TYPES[need]],
        })
    candidates.sort(key=lambda c: (c["distance_km"], -len(c["matched_needs"]), c["provider"]["organisation_name"]))
    return candidates[:limit]


def timeline(sos: SosRequest) -> list[dict[str, Any]]:
    return [{"status": status, "at": getattr(sos, _STAMP[status])} for status in STATUS_FLOW]


def provider_brief(provider) -> dict[str, Any] | None:
    if provider is None:
        return None
    return {
        "id": provider.id,
        "organisation_name": provider.organisation_name,
        "organisation_type": provider.organisation_type,
        "phone": provider.user.phone if provider.user else None,
        "latitude": provider.latitude,
        "longitude": provider.longitude,
    }


def serialize(sos: SosRequest, *, include_citizen: bool = False, distance_km: float | None = None) -> dict[str, Any]:
    data = {
        "id": sos.id,
        "status": sos.status,
        "latitude": sos.latitude,
        "longitude": sos.longitude,
        "location_source": sos.location_source,
        "accuracy_m": sos.accuracy_m,
        "emergency_type": sos.emergency_type,
        "people_affected": sos.people_affected,
        "injuries": sos.injuries,
        "needs": list(sos.needs or []),
        "vulnerable": list(sos.vulnerable or []),
        "description": sos.description,
        "contact_phone": sos.contact_phone,
        "details_submitted": sos.details_submitted_at is not None,
        "details_submitted_at": sos.details_submitted_at,
        "severity": sos_severity(sos),
        "timeline": timeline(sos),
        "assigned_provider": provider_brief(sos.assigned_provider),
        "assigned_at": sos.assigned_at,
        "created_at": sos.created_at,
        "updated_at": sos.updated_at,
        "citizen": None,
        "distance_km": None if distance_km is None else round(distance_km, 2),
    }
    if include_citizen and sos.citizen is not None:
        data["citizen"] = {"id": sos.citizen.id, "full_name": sos.citizen.full_name, "phone": sos.citizen.phone}
    return data
