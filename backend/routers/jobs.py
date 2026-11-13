"""Background jobs and scheduled cron endpoints."""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from db.database import get_db
from services.feeds.poller import poll_all_feeds

router = APIRouter(prefix="/jobs", tags=["jobs"])


def verify_cron_secret(
    x_cron_key: str | None = Header(None, alias="X-Cron-Key"),
    authorization: str | None = Header(None),
    token: str | None = Query(None),
) -> bool:
    """Validate protected cron token against CRON_SECRET in environment."""
    expected = os.getenv("CRON_SECRET", "").strip()
    if not expected:
        # No secret configured: allow execution in development/test environment
        return True

    provided = x_cron_key or token
    if not provided and authorization and authorization.startswith("Bearer "):
        provided = authorization.replace("Bearer ", "").strip()

    if provided != expected:
        raise HTTPException(status_code=401, detail="Invalid cron authorization token")
    return True


@router.post("/poll")
def run_poll_job(
    india_only: bool = Query(True, description="Filter feeds to Indian territory"),
    authorized: bool = Depends(verify_cron_secret),
    db: Session = Depends(get_db),
):
    """Protected cron endpoint to poll external disaster feeds (GDACS & USGS)."""
    return poll_all_feeds(session=db, india_only=india_only)
