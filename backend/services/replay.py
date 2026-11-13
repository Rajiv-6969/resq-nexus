"""Event Replay Service: multi-phase disaster progression reconstruction.

Allows operators to scrub and replay how a disaster unfolded across:
1. Official Warning Issuance (IMD/NDMA/CWC)
2. Sentinel-1 SAR / Satellite Damage Assessment
3. Citizen Ground SOS Report Influx
4. Allocation Engine Optimization & Resource Dispatch
5. Escalation & Operational Response
"""
from __future__ import annotations

from typing import Any

from services.scenarios import get_scenario, list_scenarios


def get_replayable_scenarios() -> list[dict[str, Any]]:
    """List scenarios that have replayable timelines."""
    out = []
    for s in list_scenarios():
        out.append({
            "id": s.id,
            "name": s.name,
            "disaster_type": s.disaster_type,
            "region": s.region,
            "state": s.state,
            "zone_count": getattr(s, "zone_count", 0),
            "total_population": getattr(s, "total_population", 0),
        })
    return out


def generate_event_timeline(scenario_id: str) -> dict[str, Any]:
    """Generate multi-frame timeline steps for time-slider event replay."""
    scenario = get_scenario(scenario_id)

    # Base coordinates
    center_lat = sum(z.latitude for z in scenario.zones) / max(len(scenario.zones), 1)
    center_lon = sum(z.longitude for z in scenario.zones) / max(len(scenario.zones), 1)

    # Sort zones by damage severity
    critical_zones = [z for z in scenario.zones if z.damage_severity >= 2]
    high_zones = [z for z in scenario.zones if z.damage_severity == 1]
    low_zones = [z for z in scenario.zones if z.damage_severity == 0]

    frames = [
        {
            "step": 0,
            "time_offset_mins": 0,
            "time_label": "T+00m",
            "phase": "OFFICIAL_ALERT",
            "phase_title": "Official Warning Issued",
            "description": f"Official {scenario.disaster_type.upper()} warning issued by disaster monitoring agency. Threat advisory broadcasted to regional control rooms.",
            "metrics": {
                "active_alerts": 1,
                "acknowledged_alerts": 0,
                "satellite_zones_detected": 0,
                "citizen_sos_count": 0,
                "resources_dispatched": 0,
            },
            "alerts": [
                {
                    "alert_code": f"ALT-REPLAY-{scenario.disaster_type[:3].upper()}-01",
                    "sender": "IMD (India Meteorological Department)",
                    "headline": f"CRITICAL {scenario.disaster_type.upper()} WARNING: {scenario.name}",
                    "severity": "Extreme",
                    "status": "ACTIVE",
                    "latitude": center_lat,
                    "longitude": center_lon,
                }
            ],
            "highlighted_zone_ids": [z.id for z in critical_zones[:3]],
            "active_sos": [],
            "dispatches": [],
        },
        {
            "step": 1,
            "time_offset_mins": 30,
            "time_label": "T+30m",
            "phase": "SATELLITE_PASS",
            "phase_title": "Sentinel-1 SAR / Satellite Pass",
            "description": "Copernicus Sentinel-1 Synthetic Aperture Radar pass processed. Flood backscatter thresholding identifies severe inundation and structural damage.",
            "metrics": {
                "active_alerts": 1,
                "acknowledged_alerts": 0,
                "satellite_zones_detected": len(critical_zones),
                "citizen_sos_count": 0,
                "resources_dispatched": 0,
            },
            "alerts": [
                {
                    "alert_code": f"ALT-REPLAY-{scenario.disaster_type[:3].upper()}-01",
                    "sender": "IMD (India Meteorological Department)",
                    "headline": f"CRITICAL {scenario.disaster_type.upper()} WARNING: {scenario.name}",
                    "severity": "Extreme",
                    "status": "ACTIVE",
                    "latitude": center_lat,
                    "longitude": center_lon,
                }
            ],
            "highlighted_zone_ids": [z.id for z in critical_zones],
            "active_sos": [],
            "dispatches": [],
        },
        {
            "step": 2,
            "time_offset_mins": 60,
            "time_label": "T+60m",
            "phase": "CITIZEN_SOS",
            "phase_title": "Citizen Ground SOS Influx",
            "description": "Distress calls and one-tap SOS reports arrive from citizens on the ground with GPS locations, trapped counts and urgent medical needs.",
            "metrics": {
                "active_alerts": 1,
                "acknowledged_alerts": 1,
                "satellite_zones_detected": len(critical_zones),
                "citizen_sos_count": min(len(critical_zones) * 3, 24),
                "resources_dispatched": 0,
            },
            "alerts": [
                {
                    "alert_code": f"ALT-REPLAY-{scenario.disaster_type[:3].upper()}-01",
                    "sender": "IMD (India Meteorological Department)",
                    "headline": f"CRITICAL {scenario.disaster_type.upper()} WARNING: {scenario.name}",
                    "severity": "Extreme",
                    "status": "ACKNOWLEDGED",
                    "latitude": center_lat,
                    "longitude": center_lon,
                }
            ],
            "highlighted_zone_ids": [z.id for z in critical_zones],
            "active_sos": [
                {
                    "id": f"SOS-{i+1}",
                    "latitude": z.latitude + 0.002 * (i % 2 - 0.5),
                    "longitude": z.longitude + 0.002 * ((i // 2) % 2 - 0.5),
                    "people_affected": 2 + (i * 3) % 8,
                    "needs": ["rescue_teams", "medical_kits"] if i % 2 == 0 else ["food_packets", "shelters"],
                    "status": "PENDING",
                }
                for i, z in enumerate(critical_zones[:8])
            ],
            "dispatches": [],
        },
        {
            "step": 3,
            "time_offset_mins": 90,
            "time_label": "T+90m",
            "phase": "ALLOCATION_DISPATCH",
            "phase_title": "Allocation Engine & Dispatch",
            "description": "Allocation Engine executes priority-weighted, fairness-aware optimization across real OSM road network. Nearest ambulances, rescue boats, and supplies dispatched.",
            "metrics": {
                "active_alerts": 0,
                "acknowledged_alerts": 1,
                "satellite_zones_detected": len(critical_zones),
                "citizen_sos_count": min(len(critical_zones) * 3, 24),
                "resources_dispatched": min(len(critical_zones), 12),
            },
            "alerts": [
                {
                    "alert_code": f"ALT-REPLAY-{scenario.disaster_type[:3].upper()}-01",
                    "sender": "IMD (India Meteorological Department)",
                    "headline": f"CRITICAL {scenario.disaster_type.upper()} WARNING: {scenario.name}",
                    "severity": "Extreme",
                    "status": "ACKNOWLEDGED",
                    "latitude": center_lat,
                    "longitude": center_lon,
                }
            ],
            "highlighted_zone_ids": [z.id for z in critical_zones],
            "active_sos": [
                {
                    "id": f"SOS-{i+1}",
                    "latitude": z.latitude,
                    "longitude": z.longitude,
                    "people_affected": 2 + (i * 3) % 8,
                    "status": "DISPATCHED",
                }
                for i, z in enumerate(critical_zones[:8])
            ],
            "dispatches": [
                {
                    "dispatch_id": f"DSP-{i+1:03d}",
                    "target_zone": z.name,
                    "latitude": z.latitude,
                    "longitude": z.longitude,
                    "resource_type": "rescue_teams" if i % 2 == 0 else "medical_kits",
                    "quantity": 2,
                    "status": "EN_ROUTE",
                }
                for i, z in enumerate(critical_zones[:6])
            ],
        },
        {
            "step": 4,
            "time_offset_mins": 120,
            "time_label": "T+120m",
            "phase": "RESPONSE_ESCALATION",
            "phase_title": "Escalation & Relief Operations",
            "description": "Field teams on site. Citizens evacuated to nearest open shelters. Unacknowledged sub-districts auto-escalated to state disaster response force (SDRF).",
            "metrics": {
                "active_alerts": 0,
                "acknowledged_alerts": 1,
                "satellite_zones_detected": len(critical_zones),
                "citizen_sos_count": min(len(critical_zones) * 3, 24),
                "resources_dispatched": min(len(critical_zones), 12),
                "resolved_count": min(len(critical_zones) // 2, 6),
            },
            "alerts": [
                {
                    "alert_code": f"ALT-REPLAY-{scenario.disaster_type[:3].upper()}-01",
                    "sender": "IMD (India Meteorological Department)",
                    "headline": f"CRITICAL {scenario.disaster_type.upper()} WARNING: {scenario.name}",
                    "severity": "Extreme",
                    "status": "ACKNOWLEDGED",
                    "latitude": center_lat,
                    "longitude": center_lon,
                }
            ],
            "highlighted_zone_ids": [z.id for z in critical_zones],
            "active_sos": [
                {
                    "id": f"SOS-{i+1}",
                    "latitude": z.latitude,
                    "longitude": z.longitude,
                    "people_affected": 2 + (i * 3) % 8,
                    "status": "RESOLVED" if i < 4 else "DISPATCHED",
                }
                for i, z in enumerate(critical_zones[:8])
            ],
            "dispatches": [
                {
                    "dispatch_id": f"DSP-{i+1:03d}",
                    "target_zone": z.name,
                    "latitude": z.latitude,
                    "longitude": z.longitude,
                    "resource_type": "rescue_teams" if i % 2 == 0 else "medical_kits",
                    "quantity": 2,
                    "status": "DELIVERED" if i < 3 else "EN_ROUTE",
                }
                for i, z in enumerate(critical_zones[:6])
            ],
        },
    ]

    return {
        "scenario_id": scenario.id,
        "scenario_name": scenario.name,
        "disaster_type": scenario.disaster_type,
        "center": {"latitude": round(center_lat, 4), "longitude": round(center_lon, 4)},
        "bbox": scenario.bbox,
        "total_steps": len(frames),
        "frames": frames,
    }
