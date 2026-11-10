"""Resources near a location, nearest first."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from db.database import engine, get_db
from db.geo import within_radius
from db.models import RESOURCE_TYPES, Resource, User
from deps import get_current_user
from schemas import NearbyResources
from services import resources as resource_service
from services.geo import sort_by_distance

router = APIRouter(prefix="/resources", tags=["resources"])


def parse_types(types: str | None) -> list[str] | None:
    """'HOSPITAL,SHELTER' -> ['HOSPITAL', 'SHELTER']; 422 for an unknown type."""
    if not types:
        return None
    wanted = [t.strip().upper() for t in types.split(",") if t.strip()]
    unknown = sorted(set(wanted) - set(RESOURCE_TYPES))
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown resource type: {', '.join(unknown)}. Use {', '.join(RESOURCE_TYPES)}.")
    return wanted


@router.get("/nearby", response_model=NearbyResources)
def nearby_resources(
    lat: float = Query(..., ge=-90, le=90, description="Latitude of the user"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude of the user"),
    radius_km: float = Query(10, gt=0, le=500, description="Search radius in kilometres"),
    types: str | None = Query(None, description="Comma-separated types, e.g. HOSPITAL,SHELTER (default: all)"),
    limit: int = Query(200, ge=1, le=500),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Hospitals, ambulances, shelters, food and water points, fire and police stations within the radius,
    sorted by haversine distance."""
    wanted = parse_types(types)
    query = (select(Resource).options(selectinload(Resource.provider))
             .where(within_radius(Resource, lat, lon, radius_km, engine)))
    if wanted:
        query = query.where(Resource.resource_type.in_(wanted))
    ranked = sort_by_distance(db.scalars(query), lat, lon, key=lambda r: (r.latitude, r.longitude),
                              name=lambda r: r.name, radius_km=radius_km)[:limit]
    return {
        "origin": {"latitude": lat, "longitude": lon},
        "radius_km": radius_km,
        "count": len(ranked),
        "resources": [resource_service.serialize(resource, distance) for resource, distance in ranked],
    }
