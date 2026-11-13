"""Official alerts API: feeds, acknowledgment, auto-escalation, and metrics."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import OfficialAlert, utcnow
from deps import get_current_user, require_admin
from services import alerts as alert_service

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertOut(BaseModel):
    id: int
    alert_code: str
    sender: str
    headline: str
    description: str
    severity: str
    urgency: str
    certainty: str
    disaster_type: str
    area_desc: str
    latitude: float
    longitude: float
    source: str
    status: str
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    escalated_at: datetime | None = None
    escalation_timeout_mins: int
    created_at: datetime
    updated_at: datetime


class SimulateAlertRequest(BaseModel):
    sender: str = "IMD (India Meteorological Department)"
    headline: str
    description: str
    severity: str = "Extreme"  # Extreme | Severe | Moderate | Minor
    urgency: str = "Immediate"
    certainty: str = "Observed"
    disaster_type: str = "flood"
    area_desc: str
    latitude: float
    longitude: float
    escalation_timeout_mins: int = 15


@router.get("", response_model=list[AlertOut])
def get_alerts(
    status: str | None = Query(None, description="Filter by status: ACTIVE, ACKNOWLEDGED, ESCALATED"),
    disaster_type: str | None = Query(None, description="Filter by disaster type: flood, cyclone, earthquake"),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Retrieve official alerts feed with automatic escalation tracking."""
    return alert_service.list_alerts(db, status=status, disaster_type=disaster_type, limit=limit)


@router.get("/metrics")
def get_alert_metrics(db: Session = Depends(get_db)):
    """Summary metrics: total alerts, acknowledgment rate, escalation count."""
    return alert_service.compute_alert_metrics(db)


@router.get("/{alert_id}", response_model=AlertOut)
def get_single_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = alert_service.get_alert_by_id(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert with id {alert_id} not found")
    return alert


@router.post("/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge_alert_endpoint(
    alert_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Acknowledge an active or escalated disaster alert."""
    ack_user = getattr(user, "email", "control_room_operator")
    alert = alert_service.acknowledge_alert(db, alert_id, acknowledged_by=ack_user)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert with id {alert_id} not found")
    return alert


@router.post("/simulate", response_model=AlertOut)
def simulate_new_alert(
    body: SimulateAlertRequest,
    db: Session = Depends(get_db),
    user=Depends(require_admin),
):
    """Simulate arrival of a live official disaster alert."""
    code = f"ALT-LIVE-{uuid.uuid4().hex[:6].upper()}"
    alert = OfficialAlert(
        alert_code=code,
        sender=body.sender,
        headline=body.headline,
        description=body.description,
        severity=body.severity,
        urgency=body.urgency,
        certainty=body.certainty,
        disaster_type=body.disaster_type,
        area_desc=body.area_desc,
        latitude=body.latitude,
        longitude=body.longitude,
        source="official-simulated",
        status="ACTIVE",
        escalation_timeout_mins=body.escalation_timeout_mins,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert
