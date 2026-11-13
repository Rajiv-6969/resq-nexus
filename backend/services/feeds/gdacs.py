"""GDACS (Global Disaster Alert and Coordination System) live feed client.

Polls GDACS live API for cyclones, floods, and earthquakes, filtering to
India by default, with retries and offline fixture fallback.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

GDACS_FEED_URL = "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?eventtypes=EQ,TC,FL"
FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "feeds"

INDIA_BBOX = {"south": 6.0, "north": 38.0, "west": 68.0, "east": 98.0}


def fetch_gdacs_events(
    url: str = GDACS_FEED_URL,
    india_only: bool = True,
    timeout: float = 7.0,
    retries: int = 2,
) -> list[dict[str, Any]]:
    """Poll GDACS disaster feed, returning standardized alert records."""
    if os.getenv("OFFLINE_MODE", "0") == "1":
        return _load_fixture(india_only=india_only)

    data = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "ResQ-Nexus/0.3.0 (Disaster-Response-Prototype)"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                break
        except Exception as e:
            logger.info(f"GDACS poll attempt {attempt+1} failed: {e}")

    if not data:
        logger.warning("GDACS poll failed; falling back to offline fixture")
        return _load_fixture(india_only=india_only)

    features = data.get("features", []) if isinstance(data, dict) else []
    return _parse_features(features, india_only=india_only)


def _load_fixture(india_only: bool = True) -> list[dict[str, Any]]:
    fixture_path = FIXTURES_DIR / "gdacs.json"
    if fixture_path.is_file():
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        features = data.get("features", []) if isinstance(data, dict) else []
        return _parse_features(features, india_only=india_only)
    return []


def _parse_features(features: list[dict[str, Any]], india_only: bool = True) -> list[dict[str, Any]]:
    results = []
    for f in features:
        props = f.get("properties", {})
        geom = f.get("geometry", {})
        coords = geom.get("coordinates", [])
        if len(coords) < 2:
            continue
        lon, lat = coords[0], coords[1]
        country = str(props.get("country", "")).lower()

        if india_only:
            is_in_bbox = (
                INDIA_BBOX["south"] <= lat <= INDIA_BBOX["north"] and INDIA_BBOX["west"] <= lon <= INDIA_BBOX["east"]
            )
            is_india = "india" in country
            if not (is_in_bbox or is_india):
                continue

        event_type = props.get("eventtype", "FL")
        if event_type == "TC":
            disaster = "cyclone"
        elif event_type == "EQ":
            disaster = "earthquake"
        else:
            disaster = "flood"

        alert_level = str(props.get("alertlevel", "Orange")).capitalize()
        if alert_level == "Red":
            severity = "Extreme"
        elif alert_level == "Orange":
            severity = "Severe"
        else:
            severity = "Moderate"

        event_id = str(props.get("eventid") or props.get("name") or "evt")
        name = props.get("name") or props.get("eventname") or f"Disaster {event_id}"
        desc = props.get("description") or f"GDACS warning for {name} ({country.capitalize()})."

        results.append({
            "alert_code": f"ALT-GDACS-{event_id}",
            "sender": "GDACS (UN / European Commission)",
            "headline": f"{alert_level.upper()} ALERT: {name}",
            "description": desc,
            "severity": severity,
            "urgency": "Immediate",
            "certainty": "Observed",
            "disaster_type": disaster,
            "area_desc": props.get("country", "India"),
            "latitude": float(lat),
            "longitude": float(lon),
            "source": "official-gdacs",
            "escalation_timeout_mins": 25,
        })
    return results
