"""Sentinel-1 SAR flood mapping HTTP API."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.imagery import sentinel

router = APIRouter(prefix="/sentinel", tags=["sentinel"])


class BBoxModel(BaseModel):
    south: float
    west: float
    north: float
    east: float


class SearchScenesRequest(BaseModel):
    bbox: BBoxModel
    start_date: str | None = None
    end_date: str | None = None
    limit: int = 5


class FloodAssessRequest(BaseModel):
    bbox: BBoxModel
    scenario_id: str | None = None
    water_threshold_db: float = -16.0


@router.get("/status")
def sentinel_status():
    """Report availability of Sentinel-1 UNet weights and deferred fallback state."""
    model_avail = sentinel.is_flood_model_available()
    return {
        "service": "Copernicus Sentinel-1 SAR Flood Mapping",
        "stac_catalog": "Microsoft Planetary Computer (sentinel-1-rtc)",
        "model_installed": model_avail,
        "weights_deferred": not model_avail,
        "active_mode": "unet_segmentation" if model_avail else "sar_backscatter_thresholding",
        "default_threshold_db": -16.0,
        "notice": (
            "Sentinel-1 UNet weights loaded."
            if model_avail
            else "Deferred weights fallback active (Sen1Floods11 VV backscatter thresholding < -16 dB)."
        ),
    }


@router.post("/search")
def search_sentinel_imagery(body: SearchScenesRequest):
    """Search Sentinel-1 RTC Synthetic Aperture Radar scenes via Planetary Computer STAC."""
    scenes = sentinel.search_sentinel_scenes(
        bbox=body.bbox.model_dump(),
        start_date=body.start_date,
        end_date=body.end_date,
        limit=body.limit,
    )
    return {"scenes": scenes, "count": len(scenes)}


@router.post("/assess")
def assess_sar_flood(body: FloodAssessRequest):
    """Run Sentinel-1 SAR flood mapping (with deferred weights fallback if weights absent)."""
    return sentinel.assess_flood_extent(
        bbox=body.bbox.model_dump(),
        scenario_id=body.scenario_id,
        water_threshold_db=body.water_threshold_db,
    )
