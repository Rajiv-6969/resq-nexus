"""Demo data: loads data/demo_seed.json (SYNTHETIC) into an empty database."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.models import OfficialAlert, Provider, Resource, SosRequest, User, utcnow
from services.security import hash_password
from services.sos import NEEDS, VULNERABLE_GROUPS

from paths import DEMO_SEED, SCENARIO_DIR

# Demo passwords, one per role. They are public on purpose: the README lists them and
# the login page's Demo Login buttons fill them in. Every seeded account of a role shares
# its password (and one bcrypt hash, which keeps start-up fast).
DEMO_PASSWORDS = {"ADMIN": "Admin#2026", "SERVICE_PROVIDER": "Provider#2026", "CITIZEN": "Citizen#2026"}


def seed_demo_data(session: Session, path: Path = DEMO_SEED, now: datetime | None = None, scenario_dir: Path = SCENARIO_DIR) -> bool:
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
            injuries=details.get("injuries"), needs=[n for n in NEEDS if n in details.get("needs", [])],
            vulnerable=[g for g in VULNERABLE_GROUPS if g in details.get("vulnerable", [])],
            description=details.get("description"), contact_phone=details.get("contact_phone"),
            details_submitted_at=submitted, status=s["status"], assigned_provider=providers.get(s["provider"]),
            assigned_at=events[0], acknowledged_at=events[1], dispatched_at=events[2], resolved_at=events[3],
            created_at=created, updated_at=max(t for t in [created, submitted, *events] if t is not None),
        ))

    session.add_all([*citizens.values(), *providers.values(), *resources, *requests])
    session.add_all(osm_facility_resources(scenario_dir, created_at=ago(30 * 1440)))
    session.add_all(demo_official_alerts(now=now))
    session.commit()
    return True


def demo_official_alerts(now: datetime | None = None) -> list[OfficialAlert]:
    """Default official disaster alerts for demonstration."""
    now = now or utcnow()

    def ago(minutes: float) -> datetime:
        return now - timedelta(minutes=minutes)

    return [
        OfficialAlert(
            alert_code="ALT-IMD-BLR-01",
            sender="IMD (India Meteorological Department)",
            headline="FLASH FLOOD RED ALERT: Bellandur & Varthur Catchments",
            description="Extremely heavy precipitation (>140mm in 3h) recorded. Severe waterlogging, lake overflow risk across Bellandur, Marathahalli and Outer Ring Road corridors.",
            severity="Extreme",
            urgency="Immediate",
            certainty="Observed",
            disaster_type="flood",
            area_desc="Bellandur, Bengaluru",
            latitude=12.9352,
            longitude=77.6748,
            source="official-imd",
            status="ACTIVE",
            escalation_timeout_mins=20,
            created_at=ago(10),
            updated_at=ago(10),
        ),
        OfficialAlert(
            alert_code="ALT-CWC-ALU-02",
            sender="CWC (Central Water Commission)",
            headline="SEVERE FLOOD BULLETIN: Periyar River Level Warning",
            description="Periyar river gauge at Aluva exceeds danger mark (4.2m above normal). Downstream low-lying zones advised immediate evacuation.",
            severity="Extreme",
            urgency="Immediate",
            certainty="Observed",
            disaster_type="flood",
            area_desc="Aluva Riverfront, Ernakulam",
            latitude=10.1076,
            longitude=76.3516,
            source="official-cwc",
            status="ACKNOWLEDGED",
            acknowledged_at=ago(25),
            acknowledged_by="Control Room Admin",
            escalation_timeout_mins=30,
            created_at=ago(60),
            updated_at=ago(25),
        ),
        OfficialAlert(
            alert_code="ALT-IMD-VSKP-03",
            sender="IMD (Cyclone Warning Centre)",
            headline="SEVERE CYCLONIC STORM WARNING: North Andhra Coast",
            description="Wind speeds 95-115 km/h with heavy surge inundation. Coastal Fishermen and beach front settlements instructed to evacuate to relief shelters.",
            severity="Severe",
            urgency="Immediate",
            certainty="Likely",
            disaster_type="cyclone",
            area_desc="Visakhapatnam Coast",
            latitude=17.6868,
            longitude=83.2185,
            source="official-imd",
            status="ESCALATED",
            escalated_at=ago(15),
            escalation_timeout_mins=15,
            created_at=ago(90),
            updated_at=ago(15),
        ),
        OfficialAlert(
            alert_code="ALT-NDMA-CBE-04",
            sender="NDMA (National Disaster Management Authority)",
            headline="EARTHQUAKE ADVISORY: M5.2 Tremor Reported",
            description="Magnitude 5.2 seismic event with epicenter near Western Ghats boundary. Structural inspection teams mobilized for old masonry buildings.",
            severity="Moderate",
            urgency="Expected",
            certainty="Observed",
            disaster_type="earthquake",
            area_desc="Coimbatore Central & Foothills",
            latitude=11.0168,
            longitude=76.9558,
            source="official-ndma",
            status="ACTIVE",
            escalation_timeout_mins=45,
            created_at=ago(15),
            updated_at=ago(15),
        ),
    ]


def osm_facility_resources(directory: Path = SCENARIO_DIR, created_at: datetime | None = None) -> list[Resource]:
    """Real OpenStreetMap facilities from every scenario file, as editable resources (source="osm")."""
    from services.geo.facilities import facilities_to_resources

    created_at = created_at or utcnow()
    out: list[Resource] = []
    seen: set[str] = set()
    for path in sorted(Path(directory).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for row in facilities_to_resources(data.get("facilities", []), region=data.get("region", ""), area_fallback=data.get("state", "")):
            if row["osm_id"] in seen:
                continue
            seen.add(row["osm_id"])
            out.append(Resource(**row, created_at=created_at, updated_at=created_at))
    return out
