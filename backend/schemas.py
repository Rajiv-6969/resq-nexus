"""Request and response models shared by the routers, with input validation.

Validation messages are written for people ("Enter a valid email address."), because
the frontend shows them next to the form fields.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from services.security import MAX_PASSWORD_BYTES

Role = Literal["CITIZEN", "SERVICE_PROVIDER", "ADMIN"]
ResourceType = Literal["HOSPITAL", "AMBULANCE", "SHELTER", "FOOD", "WATER", "FIRE_STATION", "POLICE"]
ResourceStatus = Literal["OPEN", "FULL", "CLOSED"]
ApprovalStatus = Literal["PENDING", "APPROVED", "REJECTED"]

_EMAIL = re.compile(r"^[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+$")
_PHONE = re.compile(r"^\+?[0-9][0-9 ()-]*[0-9]$")


def _email(value: str) -> str:
    value = value.strip().lower()
    if len(value) > 254 or not _EMAIL.match(value):
        raise ValueError("Enter a valid email address.")
    return value


def _password(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes.")
    if not (re.search(r"[A-Za-z]", value) and re.search(r"[0-9]", value)):
        raise ValueError("Password must contain a letter and a number.")
    return value


def _name(value: str) -> str:
    value = " ".join(value.split())
    if len(value) < 2:
        raise ValueError("Enter your name (at least 2 characters).")
    if len(value) > 80:
        raise ValueError("Name must be at most 80 characters.")
    return value


def _phone(value: str) -> str:
    value = " ".join(value.split())
    digits = sum(ch.isdigit() for ch in value)
    if not _PHONE.match(value) or not 7 <= digits <= 15 or len(value) > 20:
        raise ValueError("Enter a valid phone number (7 to 15 digits).")
    return value


def _text(limit: int, label: str):
    def check(value: str) -> str:
        value = " ".join(value.split())
        if len(value) > limit:
            raise ValueError(f"{label} must be at most {limit} characters.")
        return value

    return check


def _organisation(value: str) -> str:
    value = " ".join(value.split())
    if not 2 <= len(value) <= 120:
        raise ValueError("Enter the organisation name (2 to 120 characters).")
    return value


Email = Annotated[str, AfterValidator(_email)]
Password = Annotated[str, AfterValidator(_password)]
PersonName = Annotated[str, AfterValidator(_name)]
Phone = Annotated[str, AfterValidator(_phone)]
OrganisationName = Annotated[str, AfterValidator(_organisation)]
Address = Annotated[str, AfterValidator(_text(160, "Address"))]
Latitude = Annotated[float, Field(ge=-90, le=90)]
Longitude = Annotated[float, Field(ge=-180, le=180)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Orm(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --------------------------------------------------------------------------- auth
class CitizenRegister(Strict):
    full_name: PersonName
    email: Email
    password: Password
    phone: Phone | None = None


class ProviderRegister(Strict):
    full_name: PersonName
    email: Email
    password: Password
    phone: Phone
    organisation_name: OrganisationName
    organisation_type: ResourceType
    latitude: Latitude
    longitude: Longitude
    address: Address | None = None


class LoginRequest(Strict):
    email: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=200)


class ProviderOut(Orm):
    id: int
    organisation_name: str
    organisation_type: ResourceType
    latitude: float
    longitude: float
    address: str | None
    region: str | None
    approval_status: ApprovalStatus
    review_note: str | None
    reviewed_at: datetime | None
    created_at: datetime


class UserOut(Orm):
    id: int
    email: str
    full_name: str
    phone: str | None
    role: Role
    is_active: bool
    created_at: datetime
    provider: ProviderOut | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: UserOut


class ProviderRegistered(TokenResponse):
    message: str


# --------------------------------------------------------------------------- SOS
EmergencyType = Literal["flood", "earthquake", "wildfire", "cyclone", "fire", "medical", "other"]
Injuries = Literal["none", "minor", "serious", "critical"]
Need = Literal["rescue", "medical", "ambulance", "food", "water", "shelter"]
VulnerableGroup = Literal["children", "elderly", "disabled", "pregnant"]
SosStatus = Literal["PENDING", "ACKNOWLEDGED", "DISPATCHED", "RESOLVED"]
SeverityLevel = Literal["Critical", "High", "Medium", "Low"]

_NEED_ORDER = ("rescue", "medical", "ambulance", "food", "water", "shelter")
_GROUP_ORDER = ("children", "elderly", "disabled", "pregnant")


def _needs(values: list[str]) -> list[str]:
    if not values:
        raise ValueError("Choose at least one need.")
    return [need for need in _NEED_ORDER if need in values]


def _groups(values: list[str]) -> list[str]:
    return [group for group in _GROUP_ORDER if group in values]


class SosCreate(Strict):
    latitude: Latitude
    longitude: Longitude
    location_source: Literal["gps", "pin"]
    accuracy_m: float | None = Field(None, ge=0, le=100_000)


class SosDetails(Strict):
    emergency_type: EmergencyType
    people_affected: int = Field(ge=1, le=10_000)
    injuries: Injuries
    needs: Annotated[list[Need], AfterValidator(_needs)]
    vulnerable: Annotated[list[VulnerableGroup], AfterValidator(_groups)] = []
    description: Annotated[str, AfterValidator(_text(500, "Description"))] = ""
    contact_phone: Phone


class Severity(BaseModel):
    score: float
    level: SeverityLevel


class TimelineStep(BaseModel):
    status: SosStatus
    at: datetime | None


class ProviderBrief(BaseModel):
    id: int
    organisation_name: str
    organisation_type: ResourceType
    phone: str | None
    latitude: float
    longitude: float


class CitizenBrief(BaseModel):
    id: int
    full_name: str
    phone: str | None


class SosOut(BaseModel):
    id: int
    status: SosStatus
    latitude: float
    longitude: float
    location_source: Literal["gps", "pin"]
    accuracy_m: float | None
    emergency_type: EmergencyType | None
    people_affected: int | None
    injuries: Injuries | None
    needs: list[Need]
    vulnerable: list[VulnerableGroup]
    description: str | None
    contact_phone: str | None
    details_submitted: bool
    details_submitted_at: datetime | None
    severity: Severity | None
    timeline: list[TimelineStep]
    assigned_provider: ProviderBrief | None
    assigned_at: datetime | None
    created_at: datetime
    updated_at: datetime
    citizen: CitizenBrief | None = None
    distance_km: float | None = None


# --------------------------------------------------------------------------- resources
class ResourceProvider(BaseModel):
    id: int
    organisation_name: str


class ResourceOut(BaseModel):
    id: int
    name: str
    resource_type: ResourceType
    type_label: str
    latitude: float
    longitude: float
    area: str | None
    region: str | None
    contact_phone: str | None
    capacity_total: int
    capacity_available: int
    unit: str
    status: ResourceStatus
    provider: ResourceProvider | None
    updated_at: datetime
    distance_km: float | None = None


class Point(BaseModel):
    latitude: float
    longitude: float


class NearbyResources(BaseModel):
    origin: Point
    radius_km: float
    count: int
    resources: list[ResourceOut]
