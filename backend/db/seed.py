"""Demo data: loads backend/data/demo_seed.json (SYNTHETIC) into an empty database."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models import Provider, Resource, SosRequest, User, utcnow
from services.security import hash_password

DEMO_SEED = Path(__file__).resolve().parent.parent / "data" / "demo_seed.json"

# Demo passwords, one per role. They are public on purpose: the README lists them and
# the login page's Demo Login buttons fill them in. Every seeded account of a role shares
# its password (and one bcrypt hash, which keeps start-up fast).
DEMO_PASSWORDS = {"ADMIN": "Admin#2026", "SERVICE_PROVIDER": "Provider#2026", "CITIZEN": "Citizen#2026"}


def seed_demo_data(session: Session, path: Path = DEMO_SEED, now: datetime | None = None) -> bool:
    """Fill an empty database with the demo accounts, resources and SOS requests. Returns False if not empty."""
    if session.scalar(select(func.count()).select_from(User)):
        return False
    data = json.loads(path.read_text(encoding="utf-8"))
    now = now or utcnow()

    def ago(minutes: float) -> datetime:
        return now - timedelta(minutes=minutes)

    def maybe_ago(minutes: float | None) -> datetime | None:
        return None if minutes is None else ago(minutes)

    hashes = {role: hash_password(password) for role, password in DEMO_PASSWORDS.items()}
    admin = data["admin"]
    session.add(User(email=admin["email"], full_name=admin["full_name"], phone=admin["phone"], role="ADMIN",
                     password_hash=hashes["ADMIN"], created_at=ago(90 * 1440)))

    citizens = {}
    for i, c in enumerate(data["citizens"]):
        citizens[c["key"]] = User(email=c["email"], full_name=c["full_name"], phone=c["phone"], role="CITIZEN",
                                  password_hash=hashes["CITIZEN"], created_at=ago((40 - i) * 1440))

    providers = {}
    for i, p in enumerate(data["providers"]):
        status = p["approval_status"]
        created = ago({"APPROVED": (60 - i) * 1440, "PENDING": 45 + i * 60, "REJECTED": 4320}[status])
        user = User(email=p["email"], full_name=p["contact_name"], phone=p["phone"], role="SERVICE_PROVIDER",
                    password_hash=hashes["SERVICE_PROVIDER"], created_at=created)
        providers[p["key"]] = Provider(
            user=user, organisation_name=p["organisation_name"], organisation_type=p["organisation_type"],
            latitude=p["latitude"], longitude=p["longitude"], address=f"{p['area']}, {p['region']}", region=p["region"],
            approval_status=status, review_note=p["review_note"], created_at=created,
            reviewed_at=None if status == "PENDING" else created + timedelta(days=1),
        )

    resources = [
        Resource(
            name=r["name"], resource_type=r["resource_type"], latitude=r["latitude"], longitude=r["longitude"],
            area=r["area"], region=r["region"], contact_phone=r["contact_phone"], capacity_total=r["capacity_total"],
            capacity_available=r["capacity_available"], status=r["status"], provider=providers.get(r["provider"]),
            created_at=ago(30 * 1440), updated_at=ago(r["updated_minutes_ago"]),
        )
        for r in data["resources"]
    ]

    requests = []
    for s in data["sos_requests"]:
        created = ago(s["minutes_ago"])
        details = s["details"] or {}
        events = [maybe_ago(s[f"{step}_minutes_ago"]) for step in ("assigned", "acknowledged", "dispatched", "resolved")]
        submitted = created + timedelta(minutes=1) if details else None
        requests.append(SosRequest(
            citizen=citizens[s["citizen"]], latitude=s["latitude"], longitude=s["longitude"],
            location_source=s["location_source"], accuracy_m=s["accuracy_m"],
            emergency_type=details.get("emergency_type"), people_affected=details.get("people_affected"),
            injuries=details.get("injuries"), needs=details.get("needs", []), vulnerable=details.get("vulnerable", []),
            description=details.get("description"), contact_phone=details.get("contact_phone"),
            details_submitted_at=submitted, status=s["status"], assigned_provider=providers.get(s["provider"]),
            assigned_at=events[0], acknowledged_at=events[1], dispatched_at=events[2], resolved_at=events[3],
            created_at=created, updated_at=max(t for t in [created, submitted, *events] if t is not None),
        ))

    session.add_all([*citizens.values(), *providers.values(), *resources, *requests])
    session.commit()
    return True
