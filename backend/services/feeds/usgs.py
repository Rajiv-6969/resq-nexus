"""USGS Earthquakes GeoJSON live feed client.

Fetches global seismic data, filtered by default to the Indian subcontinent
(Lat 6.0°N–38.0°N, Lon 68.0°E–98.0°E) with retry logic and offline fixture support.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

USGS_FEED_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "feeds"

INDIA_BBOX = {"south": 6.0, "north": 38.0, "west": 68.0, "east": 98.0}


def fetch_usgs_earthquakes(
    url: str = USGS_FEED_URL,
    india_only: bool = True,
    timeout: float = 7.0,
    retries: int = 2,
) -> list[dict[str, Any]]:
    """Poll USGS earthquake feed, returning filtered alerts."""
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
            logger.info(f"USGS poll attempt {attempt+1} failed: {e}")

    if not data:
        logger.warning("USGS poll failed; falling back to offline fixture")
        return _load_fixture(india_only=india_only)

    return _parse_features(data.get("features", []), india_only=india_only)


def _load_fixture(india_only: bool = True) -> list[dict[str, Any]]:
    fixture_path = FIXTURES_DIR / "usgs.json"
    if fixture_path.is_file():
        data = json.loads(fixture_path.read_text(encoding="utf-8"))
        return _parse_features(data.get("features", []), india_only=india_only)
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

        if india_only:
            if not (INDIA_BBOX["south"] <= lat <= INDIA_BBOX["north"] and INDIA_BBOX["west"] <= lon <= INDIA_BBOX["east"]):
                continue

        mag = props.get("mag") or 0.0
        if mag >= 6.0:
            severity = "Extreme"
        elif mag >= 5.0:
            severity = "Severe"
        elif mag >= 4.0:
            severity = "Moderate"
        else:
            severity = "Minor"

        event_id = f.get("id") or str(props.get("code") or "evt")
        place = props.get("place") or "India Region"

        results.append({
            "alert_code": f"ALT-USGS-{event_id}",
            "sender": "USGS (Earthquake Hazards Program)",
            "headline": f"M {mag:.1f} Earthquake: {place}",
            "description": f"Seismic event of magnitude {mag:.1f} detected at depth {coords[2] if len(coords) > 2 else 10} km.",
            "severity": severity,
            "urgency": "Immediate",
            "certainty": "Observed",
            "disaster_type": "earthquake",
            "area_desc": place,
            "latitude": float(lat),
            "longitude": float(lon),
            "source": "official-usgs",
            "escalation_timeout_mins": 30,
        })
    return results
