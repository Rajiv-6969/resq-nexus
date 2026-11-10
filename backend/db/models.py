"""Tables: users, service-provider organisations, resources and SOS requests."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from db.database import Base, database_url
from db.geo import location_type, register_location_sync

LOCATION = location_type(database_url())

ROLES = ("CITIZEN", "SERVICE_PROVIDER", "ADMIN")
APPROVAL_STATUSES = ("PENDING", "APPROVED", "REJECTED")
RESOURCE_TYPES = ("HOSPITAL", "AMBULANCE", "SHELTER", "FOOD", "WATER", "FIRE_STATION", "POLICE")
RESOURCE_STATUSES = ("OPEN", "FULL", "CLOSED")
SOS_STATUSES = ("PENDING", "ACKNOWLEDGED", "DISPATCHED", "RESOLVED")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Timezone-aware UTC datetimes, stored as naive UTC so SQLite and PostgreSQL behave the same."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("store timezone-aware datetimes (UTC)")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        return None if value is None else value.replace(tzinfo=timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(80))
    phone: Mapped[str | None] = mapped_column(String(20))
    role: Mapped[str] = mapped_column(String(20), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    provider: Mapped[Provider | None] = relationship(back_populates="user", cascade="all, delete-orphan")


class Provider(Base):
    """A service-provider organisation (one per SERVICE_PROVIDER account); needs admin approval."""

    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    organisation_name: Mapped[str] = mapped_column(String(120))
    organisation_type: Mapped[str] = mapped_column(String(20))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    location: Mapped[str | None] = mapped_column(LOCATION)  # PostGIS POINT (lon lat), kept in sync with lat/lon
    address: Mapped[str | None] = mapped_column(String(160))
    region: Mapped[str | None] = mapped_column(String(60))
    approval_status: Mapped[str] = mapped_column(String(12), default="PENDING", index=True)
    review_note: Mapped[str | None] = mapped_column(String(200))
    reviewed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    user: Mapped[User] = relationship(back_populates="provider")
    resources: Mapped[list[Resource]] = relationship(back_populates="provider")


class Resource(Base):
    """A hospital, ambulance base, shelter, food or water point, fire station or police post."""

    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    resource_type: Mapped[str] = mapped_column(String(20), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    location: Mapped[str | None] = mapped_column(LOCATION)  # PostGIS POINT (lon lat), kept in sync with lat/lon
    area: Mapped[str | None] = mapped_column(String(80))
    region: Mapped[str | None] = mapped_column(String(60), index=True)
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    capacity_total: Mapped[int] = mapped_column(Integer, default=0)
    capacity_available: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(10), default="OPEN")
    provider_id: Mapped[int | None] = mapped_column(ForeignKey("providers.id", ondelete="SET NULL"), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    provider: Mapped[Provider | None] = relationship(back_populates="resources")


class SosRequest(Base):
    """A citizen's SOS: saved with its location first, details added later."""

    __tablename__ = "sos_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    citizen_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    location: Mapped[str | None] = mapped_column(LOCATION)  # PostGIS POINT (lon lat), kept in sync with lat/lon
    location_source: Mapped[str] = mapped_column(String(8))  # gps | pin
    accuracy_m: Mapped[float | None] = mapped_column(Float)

    emergency_type: Mapped[str | None] = mapped_column(String(20))
    people_affected: Mapped[int | None] = mapped_column(Integer)
    injuries: Mapped[str | None] = mapped_column(String(10))
    needs: Mapped[list[str]] = mapped_column(JSON, default=list)
    vulnerable: Mapped[list[str]] = mapped_column(JSON, default=list)
    description: Mapped[str | None] = mapped_column(String(500))
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    details_submitted_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    status: Mapped[str] = mapped_column(String(14), default="PENDING", index=True)
    assigned_provider_id: Mapped[int | None] = mapped_column(ForeignKey("providers.id", ondelete="SET NULL"), index=True)
    assigned_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    acknowledged_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    dispatched_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    citizen: Mapped[User] = relationship()
    assigned_provider: Mapped[Provider | None] = relationship()


register_location_sync(Provider, Resource, SosRequest)
