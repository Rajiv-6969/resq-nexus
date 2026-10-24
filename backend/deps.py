"""FastAPI dependencies for authentication and role checks."""
from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Provider, User
from services.security import TokenError, decode_access_token

_bearer = HTTPBearer(auto_error=False, description="Access token from POST /auth/login")
_CHALLENGE = {"WWW-Authenticate": "Bearer"}


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    """The logged-in user, from the Bearer token. 401 when it is missing, invalid or expired."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Log in to continue.", headers=_CHALLENGE)
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (TokenError, ValueError) as exc:
        raise HTTPException(status_code=401, detail=str(exc) or "Invalid session. Log in again.", headers=_CHALLENGE) from None
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="This account no longer exists. Log in again.", headers=_CHALLENGE)
    if not user.is_active:
        raise HTTPException(status_code=401, detail="This account has been deactivated.", headers=_CHALLENGE)
    return user


def require_roles(*roles: str):
    """Dependency that lets only the given roles through (403 for everyone else)."""

    def check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Your account does not have access to this.")
        return user

    return check


require_admin = require_roles("ADMIN")
require_citizen = require_roles("CITIZEN")
require_provider_account = require_roles("SERVICE_PROVIDER")


def require_approved_provider(user: User = Depends(require_provider_account)) -> Provider:
    """The provider organisation of the logged-in user; 403 until an admin approves it."""
    provider = user.provider
    if provider is None or provider.approval_status == "PENDING":
        raise HTTPException(status_code=403, detail="Your organisation is awaiting admin approval.")
    if provider.approval_status != "APPROVED":
        raise HTTPException(status_code=403, detail="Your organisation's registration was not approved.")
    return provider
