"""Citizen SOS requests: send (location first), add details, track status."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import SosRequest, User, utcnow
from deps import get_current_user, require_citizen
from schemas import SosCreate, SosDetails, SosOut
from services import sos as sos_service

router = APIRouter(prefix="/sos", tags=["sos"])

NOT_FOUND = "SOS request not found."


def _own_request(db: Session, sos_id: int, user: User) -> SosRequest:
    sos = db.get(SosRequest, sos_id)
    if sos is None or sos.citizen_id != user.id:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return sos


@router.post("", response_model=SosOut, status_code=201)
def send_sos(body: SosCreate, user: User = Depends(require_citizen), db: Session = Depends(get_db)):
    """Save an SOS at once with just its location; the details follow with PATCH /sos/{id}/details."""
    now = utcnow()
    sos = SosRequest(citizen_id=user.id, latitude=body.latitude, longitude=body.longitude,
                     location_source=body.location_source, accuracy_m=body.accuracy_m,
                     status="PENDING", created_at=now, updated_at=now)
    db.add(sos)
    db.commit()
    db.refresh(sos)
    return sos_service.serialize(sos)


@router.get("/mine", response_model=list[SosOut])
def my_requests(user: User = Depends(require_citizen), db: Session = Depends(get_db)):
    """The citizen's own requests, newest first."""
    rows = db.scalars(select(SosRequest).where(SosRequest.citizen_id == user.id)
                      .order_by(SosRequest.created_at.desc(), SosRequest.id.desc()))
    return [sos_service.serialize(sos) for sos in rows]


@router.get("/{sos_id}", response_model=SosOut)
def get_sos(sos_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """One request: for the citizen who sent it, its assigned provider, or an admin."""
    sos = db.get(SosRequest, sos_id)
    provider = user.provider if user.role == "SERVICE_PROVIDER" else None
    if sos is None or not (
        user.role == "ADMIN"
        or sos.citizen_id == user.id
        or (provider is not None and sos.assigned_provider_id == provider.id)
    ):
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return sos_service.serialize(sos, include_citizen=user.role != "CITIZEN")


@router.patch("/{sos_id}/details", response_model=SosOut)
def add_details(sos_id: int, body: SosDetails, user: User = Depends(require_citizen), db: Session = Depends(get_db)):
    """Add or correct the emergency details of the citizen's own request (until it is resolved)."""
    sos = _own_request(db, sos_id, user)
    if sos.status == "RESOLVED":
        raise HTTPException(status_code=409, detail="This request is already resolved, so its details can no longer change.")
    for field, value in body.model_dump().items():
        setattr(sos, field, value)
    sos.description = body.description or None  # an empty description is stored as no description
    sos.details_submitted_at = sos.updated_at = utcnow()
    db.commit()
    db.refresh(sos)
    return sos_service.serialize(sos)
