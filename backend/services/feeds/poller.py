"""Feeds poller: aggregates GDACS and USGS feeds and syncs to official_alerts."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import OfficialAlert, utcnow
from services.feeds.gdacs import fetch_gdacs_events
from services.feeds.usgs import fetch_usgs_earthquakes

logger = logging.getLogger(__name__)


def poll_all_feeds(session: Session, india_only: bool = True) -> dict[str, Any]:
    """Poll GDACS and USGS feeds, deduplicate by alert_code, and persist new alerts."""
    gdacs_alerts = fetch_gdacs_events(india_only=india_only)
    usgs_alerts = fetch_usgs_earthquakes(india_only=india_only)

    all_incoming = gdacs_alerts + usgs_alerts
    new_inserted = 0

    now = utcnow()
    for item in all_incoming:
        code = item["alert_code"]
        existing = session.scalar(select(OfficialAlert).where(OfficialAlert.alert_code == code))
        if existing:
            continue

        alert = OfficialAlert(
            alert_code=code,
            sender=item["sender"],
            headline=item["headline"],
            description=item["description"],
            severity=item["severity"],
            urgency=item["urgency"],
            certainty=item["certainty"],
            disaster_type=item["disaster_type"],
            area_desc=item["area_desc"],
            latitude=item["latitude"],
            longitude=item["longitude"],
            source=item["source"],
            status="ACTIVE",
            escalation_timeout_mins=item["escalation_timeout_mins"],
            created_at=now,
            updated_at=now,
        )
        session.add(alert)
        new_inserted += 1

    if new_inserted > 0:
        session.commit()

    total_alerts = session.query(OfficialAlert).count()

    return {
        "status": "ok",
        "gdacs_polled": len(gdacs_alerts),
        "usgs_polled": len(usgs_alerts),
        "new_alerts_inserted": new_inserted,
        "total_official_alerts": total_alerts,
    }
