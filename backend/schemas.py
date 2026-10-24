"""Request and response models shared by the routers, with input validation.

Validation messages are written for people ("Enter a valid email address."), because
the frontend shows them next to the form fields.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

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


# --------------------------------------------------------------------------- service providers
class ProviderResourceUpdate(Strict):
    capacity_total: int | None = Field(None, ge=0, le=1_000_000)
    capacity_available: int | None = Field(None, ge=0, le=1_000_000)
    status: ResourceStatus | None = None

    @model_validator(mode="after")
    def _something_to_update(self) -> ProviderResourceUpdate:
        if self.capacity_total is None and self.capacity_available is None and self.status is None:
            raise ValueError("Nothing to update: send capacity_total, capacity_available or status.")
        return self


class ProviderStatusUpdate(Strict):
    status: Literal["DISPATCHED", "RESOLVED"]


class ProviderBoard(BaseModel):
    radius_km: float
    assigned: list[SosOut]
    nearby: list[SosOut]


# --------------------------------------------------------------------------- admin
def _resource_name(value: str) -> str:
    value = " ".join(value.split())
    if not 2 <= len(value) <= 120:
        raise ValueError("Enter the resource name (2 to 120 characters).")
    return value


ResourceName = Annotated[str, AfterValidator(_resource_name)]
Area = Annotated[str, AfterValidator(_text(80, "Area"))]
Region = Annotated[str, AfterValidator(_text(60, "Region"))]
Capacity = Annotated[int, Field(ge=0, le=1_000_000)]


class SosCounts(BaseModel):
    total: int
    active: int
    pending: int
    acknowledged: int
    dispatched: int
    resolved: int


class AdminSummary(BaseModel):
    sos: SosCounts
    shelter_capacity_available: int
    ambulances_available: int
    providers_pending: int
    resources_open: int


class Suggestion(BaseModel):
    provider: ProviderBrief
    resource: ResourceOut
    distance_km: float
    matched_needs: list[Need]


class Suggestions(BaseModel):
    request_id: int
    needs: list[Need]
    radius_km: float
    candidates: list[Suggestion]


class AssignRequest(Strict):
    provider_id: int


class AdminStatusUpdate(Strict):
    status: Literal["ACKNOWLEDGED", "DISPATCHED", "RESOLVED"]


class ProviderReview(Strict):
    note: Annotated[str, AfterValidator(_text(200, "Note"))] | None = None


class ProviderContact(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str | None
    is_active: bool


class AdminProviderOut(ProviderOut):
    contact: ProviderContact
    resource_count: int
    active_requests: int


class AdminUserUpdate(Strict):
    is_active: bool


class AdminResourceCreate(Strict):
    name: ResourceName
    resource_type: ResourceType
    latitude: Latitude
    longitude: Longitude
    area: Area | None = None
    region: Region | None = None
    contact_phone: Phone | None = None
    capacity_total: Capacity
    capacity_available: Capacity
    status: ResourceStatus = "OPEN"
    provider_id: int | None = None

    @model_validator(mode="after")
    def _available_within_total(self) -> AdminResourceCreate:
        if self.capacity_available > self.capacity_total:
            raise ValueError("Available capacity cannot be more than the total.")
        return self


class AdminResourceUpdate(Strict):
    name: ResourceName | None = None
    resource_type: ResourceType | None = None
    latitude: Latitude | None = None
    longitude: Longitude | None = None
    area: Area | None = None
    region: Region | None = None
    contact_phone: Phone | None = None
    capacity_total: Capacity | None = None
    capacity_available: Capacity | None = None
    status: ResourceStatus | None = None
    provider_id: int | None = None  # send null to remove the owner

    @model_validator(mode="after")
    def _something_to_update(self) -> AdminResourceUpdate:
        if not self.model_fields_set:
            raise ValueError("Nothing to update.")
        return self
