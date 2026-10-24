"""Registration, login and the current user."""
from __future__ import annotations

import math
import os
import threading
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Provider, User
from deps import get_current_user
from schemas import CitizenRegister, LoginRequest, ProviderRegister, ProviderRegistered, TokenResponse, UserOut
from services.security import create_access_token, dummy_verify, hash_password, token_minutes, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

LOGIN_ERROR = "Incorrect email or password."
# Failed logins allowed per window, for one email from one address, and for one address overall.
MAX_FAILURES_PER_ACCOUNT = 10
MAX_FAILURES_PER_ADDRESS = 50
FAILURE_WINDOW_S = 300

_failures: dict[tuple[str, ...], deque[float]] = defaultdict(deque)
_failures_lock = threading.Lock()


def reset_login_attempts() -> None:
    with _failures_lock:
        _failures.clear()


def _client_address(request: Request) -> str:
    if os.getenv("VERCEL"):  # behind Vercel's proxy the caller is the first X-Forwarded-For entry
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _recent(key: tuple[str, ...], now: float) -> deque[float]:
    attempts = _failures[key]
    while attempts and now - attempts[0] > FAILURE_WINDOW_S:
        attempts.popleft()
    return attempts


def _check_rate_limit(keys: list[tuple[tuple[str, ...], int]]) -> None:
    now = time.monotonic()
    with _failures_lock:
        for key, limit in keys:
            attempts = _recent(key, now)
            if len(attempts) >= limit:
                wait = max(1, math.ceil(FAILURE_WINDOW_S - (now - attempts[0])))
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many failed logins. Try again in {math.ceil(wait / 60)} minute(s).",
                    headers={"Retry-After": str(wait)},
                )


def _record_failure(keys: list[tuple[tuple[str, ...], int]]) -> None:
    now = time.monotonic()
    with _failures_lock:
        for key, _ in keys:
            _recent(key, now).append(now)


def _session(user: User) -> dict:
    return {
        "access_token": create_access_token(user.id, user.role),
        "token_type": "bearer",
        "expires_in": token_minutes() * 60,
        "user": user,
    }


def _ensure_new_email(db: Session, email: str) -> None:
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists. Log in instead.")


def _save(db: Session, user: User) -> User:
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # two sign-ups with the same email at the same moment
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists. Log in instead.") from None
    db.refresh(user)
    return user


@router.post("/register", response_model=TokenResponse, status_code=201)
def register_citizen(body: CitizenRegister, db: Session = Depends(get_db)):
    """Citizens sign up themselves and are logged in straight away."""
    _ensure_new_email(db, body.email)
    user = _save(db, User(email=body.email, password_hash=hash_password(body.password),
                          full_name=body.full_name, phone=body.phone, role="CITIZEN"))
    return _session(user)


@router.post("/register/provider", response_model=ProviderRegistered, status_code=201)
def register_provider(body: ProviderRegister, db: Session = Depends(get_db)):
    """Service providers sign up with their organisation; an admin must approve it before they can respond."""
    _ensure_new_email(db, body.email)
    user = User(email=body.email, password_hash=hash_password(body.password),
                full_name=body.full_name, phone=body.phone, role="SERVICE_PROVIDER")
    user.provider = Provider(
        organisation_name=body.organisation_name, organisation_type=body.organisation_type,
        latitude=body.latitude, longitude=body.longitude, address=body.address or None, approval_status="PENDING",
    )
    _save(db, user)
    return {
        **_session(user),
        "message": "Registration received. An admin must approve your organisation before you can respond to SOS requests.",
    }


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """Email + password -> access token (send it as `Authorization: Bearer <token>`)."""
    email = body.email.strip().lower()
    address = _client_address(request)
    limits = [(("account", address, email), MAX_FAILURES_PER_ACCOUNT), (("address", address), MAX_FAILURES_PER_ADDRESS)]
    _check_rate_limit(limits)

    user = db.scalars(select(User).where(User.email == email)).first()
    if user is None:
        dummy_verify(body.password)  # same work as a real check, so unknown emails can't be detected by timing
    if user is None or not verify_password(body.password, user.password_hash):
        _record_failure(limits)
        raise HTTPException(status_code=401, detail=LOGIN_ERROR)
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated. Contact an administrator.")
    with _failures_lock:
        _failures.pop(("account", address, email), None)
    return _session(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    """The logged-in user (and their organisation, for service providers)."""
    return user
