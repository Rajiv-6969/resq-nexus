"""Official alerts management, tracking, acknowledgment, and automatic escalation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models import OfficialAlert, utcnow


def check_and_escalate_alerts(session: Session, now: datetime | None = None) -> int:
    """Escalate any active alert whose escalation timeout has expired."""
    now = now or utcnow()
    active_alerts = session.scalars(
        select(OfficialAlert).where(OfficialAlert.status == "ACTIVE")
    ).all()

    escalated_count = 0
    for alert in active_alerts:
        timeout_delta = timedelta(minutes=alert.escalation_timeout_mins or 30)
        if alert.created_at + timeout_delta <= now:
            alert.status = "ESCALATED"
            alert.escalated_at = now
            alert.updated_at = now
            escalated_count += 1

    if escalated_count > 0:
        session.commit()
    return escalated_count


def list_alerts(
    session: Session,
    status: str | None = None,
    disaster_type: str | None = None,
    limit: int = 50,
) -> list[OfficialAlert]:
    """Retrieve tracked official alerts, automatically processing escalations."""
    check_and_escalate_alerts(session)
    query = select(OfficialAlert).order_by(OfficialAlert.created_at.desc())
    if status:
        query = query.where(OfficialAlert.status == status.upper())
    if disaster_type:
        query = query.where(OfficialAlert.disaster_type == disaster_type.lower())
    if limit:
        query = query.limit(limit)
    return list(session.scalars(query).all())


def get_alert_by_id(session: Session, alert_id: int) -> OfficialAlert | None:
    check_and_escalate_alerts(session)
    return session.get(OfficialAlert, alert_id)


def acknowledge_alert(session: Session, alert_id: int, acknowledged_by: str) -> OfficialAlert | None:
    """Acknowledge an active or escalated alert."""
    alert = session.get(OfficialAlert, alert_id)
    if not alert:
        return None

    now = utcnow()
    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_at = now
    alert.acknowledged_by = acknowledged_by
    alert.updated_at = now
    session.commit()
    session.refresh(alert)
    return alert


def compute_alert_metrics(session: Session) -> dict[str, Any]:
    """Compute official alert tracking metrics: count, acknowledgment rate, escalation."""
    check_and_escalate_alerts(session)
    alerts = list(session.scalars(select(OfficialAlert)).all())
    total = len(alerts)
    if total == 0:
        return {
            "total_alerts": 0,
            "active": 0,
            "acknowledged": 0,
            "escalated": 0,
            "acknowledgment_rate": 0.0,
            "mean_response_time_mins": 0.0,
        }

    active = sum(1 for a in alerts if a.status == "ACTIVE")
    acknowledged = sum(1 for a in alerts if a.status == "ACKNOWLEDGED")
    escalated = sum(1 for a in alerts if a.status == "ESCALATED")

    ack_durations = [
        (a.acknowledged_at - a.created_at).total_seconds() / 60.0
        for a in alerts
        if a.acknowledged_at and a.created_at
    ]
    mean_response = round(sum(ack_durations) / len(ack_durations), 1) if ack_durations else 0.0
    ack_rate = round(acknowledged / total, 3)

    return {
        "total_alerts": total,
        "active": active,
        "acknowledged": acknowledged,
        "escalated": escalated,
        "acknowledgment_rate": ack_rate,
        "mean_response_time_mins": mean_response,
    }
