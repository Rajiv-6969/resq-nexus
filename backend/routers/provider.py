"""Service-provider dashboard: own resources, assigned and nearby SOS requests, accept and update."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from db.database import get_db
from db.models import Provider, Resource, SosRequest, utcnow
from deps import require_approved_provider
from schemas import ProviderBoard, ProviderResourceUpdate, ProviderStatusUpdate, ResourceOut, SosOut
from services import resources as resource_service
from services import sos as sos_service
from services.geo import bounding_box, haversine_km, sort_by_distance

router = APIRouter(prefix="/provider", tags=["service provider"])

REQUEST_NOT_FOUND = "SOS request not found."


def _with_people(query):
    return query.options(selectinload(SosRequest.citizen), selectinload(SosRequest.assigned_provider))


@router.get("/resources", response_model=list[ResourceOut])
def my_resources(provider: Provider = Depends(require_approved_provider), db: Session = Depends(get_db)):
    """The resources this organisation runs."""
    rows = db.scalars(select(Resource).where(Resource.provider_id == provider.id).order_by(Resource.name))
    return [resource_service.serialize(r) for r in rows]


@router.patch("/resources/{resource_id}", response_model=ResourceOut)
def update_my_resource(resource_id: int, body: ProviderResourceUpdate,
                       provider: Provider = Depends(require_approved_provider), db: Session = Depends(get_db)):
    """Update availability (total / available) and status (OPEN, FULL, CLOSED) of an own resource."""
    resource = db.get(Resource, resource_id)
    if resource is None or resource.provider_id != provider.id:
        raise HTTPException(status_code=404, detail="Resource not found.")
    changes = body.model_dump(exclude_none=True)
    total = changes.get("capacity_total", resource.capacity_total)
    available = changes.get("capacity_available", resource.capacity_available)
    if available > total:
        raise HTTPException(status_code=422, detail=f"Available capacity ({available}) cannot be more than the total ({total}).")
    for field, value in changes.items():
        setattr(resource, field, value)
    resource.updated_at = utcnow()
    db.commit()
    db.refresh(resource)
    return resource_service.serialize(resource)


@router.get("/requests", response_model=ProviderBoard)
def request_board(radius_km: float = Query(25, gt=0, le=200, description="How far to look for unassigned requests"),
                  provider: Provider = Depends(require_approved_provider), db: Session = Depends(get_db)):
    """Requests assigned to this organisation, and unassigned PENDING requests nearby (nearest first)."""
    here = (provider.latitude, provider.longitude)
    assigned = list(db.scalars(_with_people(select(SosRequest)).where(SosRequest.assigned_provider_id == provider.id)))
    assigned.sort(key=lambda s: (s.status == "RESOLVED", -s.updated_at.timestamp()))
    south, north, west, east = bounding_box(*here, radius_km)
    open_requests = db.scalars(_with_people(select(SosRequest)).where(
        SosRequest.assigned_provider_id.is_(None), SosRequest.status == "PENDING",
        SosRequest.latitude.between(south, north), SosRequest.longitude.between(west, east),
    ))
    nearby = sort_by_distance(open_requests, *here, key=lambda s: (s.latitude, s.longitude),
                              name=lambda s: str(s.id), radius_km=radius_km)
    return {
        "radius_km": radius_km,
        "assigned": [sos_service.serialize(s, include_citizen=True, distance_km=haversine_km(*here, s.latitude, s.longitude))
                     for s in assigned],
        "nearby": [sos_service.serialize(s, include_citizen=True, distance_km=d) for s, d in nearby],
    }


def _request(db: Session, sos_id: int) -> SosRequest:
    sos = db.get(SosRequest, sos_id)
    if sos is None:
        raise HTTPException(status_code=404, detail=REQUEST_NOT_FOUND)
    return sos


def _commit(db: Session, sos: SosRequest) -> dict:
    db.commit()
    db.refresh(sos)
    return sos_service.serialize(sos, include_citizen=True)


@router.post("/requests/{sos_id}/accept", response_model=SosOut)
def accept_request(sos_id: int, provider: Provider = Depends(require_approved_provider), db: Session = Depends(get_db)):
    """Take on a PENDING request (unassigned, or assigned to this organisation): it becomes ACKNOWLEDGED."""
    sos = _request(db, sos_id)
    try:
        sos_service.accept(sos, provider.id, utcnow())
    except sos_service.TransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return _commit(db, sos)


@router.post("/requests/{sos_id}/status", response_model=SosOut)
def update_request_status(sos_id: int, body: ProviderStatusUpdate,
                          provider: Provider = Depends(require_approved_provider), db: Session = Depends(get_db)):
    """ACKNOWLEDGED -> DISPATCHED -> RESOLVED, one step at a time, for a request this organisation accepted."""
    sos = _request(db, sos_id)
    if sos.assigned_provider_id not in (None, provider.id):
        raise HTTPException(status_code=404, detail=REQUEST_NOT_FOUND)
    if sos.status == "PENDING":
        raise HTTPException(status_code=409, detail="Accept this request first.")
    try:
        sos_service.advance(sos, body.status, utcnow())
    except sos_service.TransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return _commit(db, sos)
