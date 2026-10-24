"""Passwords and access tokens.

Passwords are hashed with bcrypt through passlib; access tokens are JWTs signed
with HS256 using JWT_SECRET from backend/.env (never committed).
"""
from __future__ import annotations

import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

import jwt
from passlib.context import CryptContext

log = logging.getLogger(__name__)

ALGORITHM = "HS256"
DEFAULT_TOKEN_MINUTES = 12 * 60  # a full day of demo sessions without logging in again
MIN_SECRET_LENGTH = 32
# bcrypt reads only the first 72 bytes of a password, so longer ones are refused up front.
MAX_PASSWORD_BYTES = 72

_ephemeral_secret: str | None = None


class TokenError(ValueError):
    """The access token is missing, malformed, signed with another key or expired."""


@lru_cache(maxsize=4)
def _context(rounds: int) -> CryptContext:
    return CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=rounds)


def _pwd() -> CryptContext:
    return _context(int(os.getenv("BCRYPT_ROUNDS", "12")))


def hash_password(password: str) -> str:
    """bcrypt hash with a random salt (cost from BCRYPT_ROUNDS, default 12)."""
    return _pwd().hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _pwd().verify(password, password_hash)
    except (ValueError, TypeError):  # malformed or unknown hash format
        return False


@lru_cache(maxsize=4)
def _dummy_hash(rounds: int) -> str:
    return _context(rounds).hash(secrets.token_urlsafe(16))


def dummy_verify(password: str) -> None:
    """Spend the same time as a real check, so unknown emails can't be told apart by timing."""
    _pwd().verify(password, _dummy_hash(int(os.getenv("BCRYPT_ROUNDS", "12"))))


def signing_secret() -> str:
    """JWT_SECRET from the environment, or a temporary per-process secret with a warning."""
    global _ephemeral_secret
    secret = os.getenv("JWT_SECRET", "").strip()
    if secret:
        if len(secret) < MIN_SECRET_LENGTH:
            raise RuntimeError(
                f"JWT_SECRET must be at least {MIN_SECRET_LENGTH} characters. Generate one with: "
                'python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return secret
    if _ephemeral_secret is None:
        _ephemeral_secret = secrets.token_urlsafe(48)
        log.warning("JWT_SECRET is not set: using a temporary secret, so every login ends when the server restarts.")
    return _ephemeral_secret


def token_minutes() -> int:
    return int(os.getenv("JWT_EXPIRE_MINUTES", str(DEFAULT_TOKEN_MINUTES)))


def create_access_token(user_id: int, role: str, minutes: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    lifetime = timedelta(minutes=token_minutes() if minutes is None else minutes)
    payload = {"sub": str(user_id), "role": role, "iat": now, "exp": now + lifetime}
    return jwt.encode(payload, signing_secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, signing_secret(), algorithms=[ALGORITHM], options={"require": ["exp", "iat", "sub"]})
    except jwt.ExpiredSignatureError:
        raise TokenError("Your session has expired. Log in again.") from None
    except jwt.InvalidTokenError:
        raise TokenError("Invalid session. Log in again.") from None
