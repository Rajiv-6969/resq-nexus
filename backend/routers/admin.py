"""Admin dashboard: SOS monitor, assignment, provider approvals, users and resources."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from db.database import get_db
from db.models import APPROVAL_STATUSES, RESOURCE_STATUSES, Provider, Resource, SosRequest, User, utcnow
from deps import require_admin
from routers.resources import parse_types
from schemas import (
    AdminProviderOut,
    AdminResourceCreate,
    AdminResourceUpdate,
    AdminStatusUpdate,
    AdminSummary,
    AdminUserUpdate,
    AssignRequest,
    ProviderReview,
    ResourceOut,
    Role,
    SosOut,
    Suggestions,
    UserOut,
)
from services import resources as resource_service
from services import sos as sos_service

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

SOS_NOT_FOUND = "SOS request not found."
PROVIDER_NOT_FOUND = "Provider not found."


def _csv(value: str | None, allowed: tuple[str, ...], label: str, upper: bool = True) -> list[str] | None:
    if not value:
        return None
    items = [v.strip().upper() if upper else v.strip().lower() for v in value.split(",") if v.strip()]
    unknown = sorted(set(items) - set(allowed))
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown {label}: {', '.join(unknown)}. Use {', '.join(allowed)}.")
    return items


def _sos_or_404(db: Session, sos_id: int) -> SosRequest:
    sos = db.get(SosRequest, sos_id)
    if sos is None:
        raise HTTPException(status_code=404, detail=SOS_NOT_FOUND)
    return sos


def _provider_or_404(db: Session, provider_id: int) -> Provider:
    provider = db.get(Provider, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail=PROVIDER_NOT_FOUND)
    return provider


def _saved_sos(db: Session, sos: SosRequest) -> dict:
    db.commit()
    db.refresh(sos)
    return sos_service.serialize(sos, include_citizen=True)


# --------------------------------------------------------------------------- summary + SOS monitor
@router.get("/summary", response_model=AdminSummary)
def summary(db: Session = Depends(get_db)):
    """Counters for the SOS monitor: requests by status, open shelter places and ambulances, pending providers."""
    by_status = dict(db.execute(select(SosRequest.status, func.count()).group_by(SosRequest.status)).all())

    def available(resource_type: str) -> int:
        return int(db.scalar(select(func.coalesce(func.sum(Resource.capacity_available), 0))
                             .where(Resource.resource_type == resource_type, Resource.status == "OPEN")) or 0)

    return {
        "sos": {
            "total": sum(by_status.values()),
            "active": sum(by_status.get(s, 0) for s in sos_service.ACTIVE_STATUSES),
            **{s.lower(): by_status.get(s, 0) for s in sos_service.STATUS_FLOW},
        },
        "shelter_capacity_available": available("SHELTER"),
        "ambulances_available": available("AMBULANCE"),
        "providers_pending": db.scalar(select(func.count()).select_from(Provider).where(Provider.approval_status == "PENDING")),
        "resources_open": db.scalar(select(func.count()).select_from(Resource).where(Resource.status == "OPEN")),
    }


@router.get("/sos", response_model=list[SosOut])
def sos_monitor(
    status: str | None = Query(None, description="Comma-separated statuses, e.g. PENDING,ACKNOWLEDGED"),
    type_: str | None = Query(None, alias="type", description="Comma-separated emergency types, e.g. flood,fire"),
    db: Session = Depends(get_db),
):
    """Every SOS request: active ones first, most severe first (requests still waiting for details count
    as High), then newest."""
    statuses = _csv(status, sos_service.STATUS_FLOW, "status")
    types = _csv(type_, sos_service.EMERGENCY_TYPES, "emergency type", upper=False)
    query = select(SosRequest).options(selectinload(SosRequest.citizen),
                                       selectinload(SosRequest.assigned_provider).selectinload(Provider.user))
    if statuses:
        query = query.where(SosRequest.status.in_(statuses))
    if types:
        query = query.where(SosRequest.emergency_type.in_(types))

    def order(sos: SosRequest):
        severity = sos_service.sos_severity(sos)
        return (sos.status == "RESOLVED", -(severity["score"] if severity else 0.5), -sos.created_at.timestamp())

    return [sos_service.serialize(sos, include_citizen=True) for sos in sorted(db.scalars(query), key=order)]


@router.get("/sos/{sos_id}/suggestions", response_model=Suggestions)
def suggestions(sos_id: int, db: Session = Depends(get_db)):
    """The nearest approved providers with a suitable resource that is OPEN with capacity left."""
    sos = _sos_or_404(db, sos_id)
    providers = db.scalars(select(Provider).options(selectinload(Provider.resources), selectinload(Provider.user))
                           .where(Provider.approval_status == "APPROVED"))
    return {
        "request_id": sos.id,
        "needs": sos_service.needs_for(sos),
        "radius_km": sos_service.SUGGESTION_RADIUS_KM,
        "candidates": sos_service.suggest_providers(sos, providers),
    }


@router.post("/sos/{sos_id}/assign", response_model=SosOut)
def assign(sos_id: int, body: AssignRequest, db: Session = Depends(get_db)):
    """Give a PENDING request to an approved provider; it stays PENDING until they accept it."""
    sos = _sos_or_404(db, sos_id)
    provider = _provider_or_404(db, body.provider_id)
    if provider.approval_status != "APPROVED" or not provider.user.is_active:
        raise HTTPException(status_code=409, detail=f"{provider.organisation_name} is not approved to respond to requests.")
    if sos.status == "RESOLVED":
        raise HTTPException(status_code=409, detail="This request is already resolved.")
    if sos.status != "PENDING":
        raise HTTPException(status_code=409, detail="This request has already been accepted by a provider.")
    sos.assigned_provider_id = provider.id
    sos.assigned_at = sos.updated_at = utcnow()
    return _saved_sos(db, sos)


@router.post("/sos/{sos_id}/status", response_model=SosOut)
def set_status(sos_id: int, body: AdminStatusUpdate, db: Session = Depends(get_db)):
    """Move a request one step on for its provider, or close it (RESOLVED) from any active status."""
    sos = _sos_or_404(db, sos_id)
    now = utcnow()
    try:
        if body.status == "RESOLVED" and sos.status != "DISPATCHED":
            sos_service.resolve(sos, now)
        else:
            if sos.assigned_provider_id is None:
                raise HTTPException(status_code=409, detail="Assign a provider before moving this request on.")
            sos_service.advance(sos, body.status, now)
    except sos_service.TransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from None
    return _saved_sos(db, sos)


# --------------------------------------------------------------------------- providers
def _provider_out(provider: Provider, db: Session) -> dict:
    active = db.scalar(select(func.count()).select_from(SosRequest).where(
        SosRequest.assigned_provider_id == provider.id, SosRequest.status.in_(sos_service.ACTIVE_STATUSES)))
    user = provider.user
    return {
        **{field: getattr(provider, field) for field in (
            "id", "organisation_name", "organisation_type", "latitude", "longitude", "address", "region",
            "approval_status", "review_note", "reviewed_at", "created_at")},
        "contact": {"id": user.id, "full_name": user.full_name, "email": user.email, "phone": user.phone,
                    "is_active": user.is_active},
        "resource_count": len(provider.resources),
        "active_requests": active,
    }


@router.get("/providers", response_model=list[AdminProviderOut])
def providers(status: str | None = Query(None, description="PENDING, APPROVED or REJECTED (comma-separated)"),
              db: Session = Depends(get_db)):
    """Provider organisations, pending registrations first."""
    statuses = _csv(status, APPROVAL_STATUSES, "approval status")
    query = select(Provider).options(selectinload(Provider.user), selectinload(Provider.resources))
    if statuses:
        query = query.where(Provider.approval_status.in_(statuses))
    rows = sorted(db.scalars(query), key=lambda p: (p.approval_status != "PENDING", p.organisation_name))
    return [_provider_out(p, db) for p in rows]


@router.post("/providers/{provider_id}/approve", response_model=AdminProviderOut)
def approve_provider(provider_id: int, db: Session = Depends(get_db)):
    """Approve a pending (or earlier rejected) organisation. A first resource is created for it, CLOSED
    with no capacity, at its location, for the provider to fill in."""
    provider = _provider_or_404(db, provider_id)
    if provider.approval_status == "APPROVED":
        raise HTTPException(status_code=409, detail="This organisation is already approved.")
    now = utcnow()
    provider.approval_status, provider.review_note, provider.reviewed_at = "APPROVED", None, now
    if not provider.resources:
        provider.resources.append(Resource(
            name=provider.organisation_name, resource_type=provider.organisation_type,
            latitude=provider.latitude, longitude=provider.longitude, area=provider.address, region=provider.region,
            contact_phone=provider.user.phone, capacity_total=0, capacity_available=0, status="CLOSED",
            source="user", created_at=now, updated_at=now,
        ))
    db.commit()
    db.refresh(provider)
    return _provider_out(provider, db)


@router.post("/providers/{provider_id}/reject", response_model=AdminProviderOut)
def reject_provider(provider_id: int, body: ProviderReview | None = None, db: Session = Depends(get_db)):
    """Reject a pending registration, optionally with a reason the provider will see."""
    provider = _provider_or_404(db, provider_id)
    if provider.approval_status != "PENDING":
        raise HTTPException(status_code=409, detail="Only pending registrations can be rejected.")
    provider.approval_status = "REJECTED"
    provider.review_note = body.note if body and body.note else None
    provider.reviewed_at = utcnow()
    db.commit()
    db.refresh(provider)
    return _provider_out(provider, db)


# --------------------------------------------------------------------------- users
@router.get("/users", response_model=list[UserOut])
def users(role: Role | None = Query(None), db: Session = Depends(get_db)):
    """Every account (optionally one role), admins first."""
    query = select(User).options(selectinload(User.provider))
    if role:
        query = query.where(User.role == role)
    order = {"ADMIN": 0, "SERVICE_PROVIDER": 1, "CITIZEN": 2}
    return sorted(db.scalars(query), key=lambda u: (order[u.role], u.full_name.lower()))


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, body: AdminUserUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Deactivate (or reactivate) an account. Deactivated users can't log in and their sessions stop working."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.id == admin.id and not body.is_active:
        raise HTTPException(status_code=409, detail="You cannot deactivate your own account.")
    user.is_active = body.is_active
    db.commit()
    db.refresh(user)
    return user


# --------------------------------------------------------------------------- resources
@router.get("/resources", response_model=list[ResourceOut])
def resources(
    type_: str | None = Query(None, alias="type", description="Comma-separated resource types"),
    region: str | None = Query(None, description="Exact region name, e.g. Bengaluru"),
    status: str | None = Query(None, description="OPEN, FULL or CLOSED (comma-separated)"),
    db: Session = Depends(get_db),
):
    """Every resource, by region, type and name."""
    query = select(Resource).options(selectinload(Resource.provider))
    types = parse_types(type_)
    statuses = _csv(status, RESOURCE_STATUSES, "status")
    if types:
        query = query.where(Resource.resource_type.in_(types))
    if statuses:
        query = query.where(Resource.status.in_(statuses))
    if region:
        query = query.where(func.lower(Resource.region) == region.strip().lower())
    rows = sorted(db.scalars(query), key=lambda r: (r.region or "", r.resource_type, r.name))
    return [resource_service.serialize(r) for r in rows]


def _check_owner(db: Session, provider_id: int | None) -> None:
    if provider_id is not None:
        _provider_or_404(db, provider_id)


@router.post("/resources", response_model=ResourceOut, status_code=201)
def create_resource(body: AdminResourceCreate, db: Session = Depends(get_db)):
    _check_owner(db, body.provider_id)
    now = utcnow()
    resource = Resource(**body.model_dump(), source="user", created_at=now, updated_at=now)
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource_service.serialize(resource)


@router.patch("/resources/{resource_id}", response_model=ResourceOut)
def update_resource(resource_id: int, body: AdminResourceUpdate, db: Session = Depends(get_db)):
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found.")
    changes = body.model_dump(include=body.model_fields_set)
    for required in ("name", "resource_type", "latitude", "longitude", "capacity_total", "capacity_available", "status"):
        if required in changes and changes[required] is None:
            raise HTTPException(status_code=422, detail=f"{required} cannot be empty.")
    if "provider_id" in changes:
        _check_owner(db, changes["provider_id"])
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


@router.delete("/resources/{resource_id}", status_code=204)
def delete_resource(resource_id: int, db: Session = Depends(get_db)):
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found.")
    db.delete(resource)
    db.commit()
    return Response(status_code=204)
