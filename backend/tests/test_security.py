"""Password hashing (bcrypt via passlib) and JWT access tokens."""
import jwt
import pytest

from services import security


def test_password_hash_is_bcrypt_and_verifies():
    hashed = security.hash_password("Citizen#2026")
    assert hashed.startswith("$2b$")
    assert "Citizen#2026" not in hashed
    assert security.verify_password("Citizen#2026", hashed)
    assert not security.verify_password("citizen#2026", hashed)


def test_same_password_gets_a_different_salt_each_time():
    assert security.hash_password("Citizen#2026") != security.hash_password("Citizen#2026")


def test_verify_password_is_false_for_a_malformed_hash():
    assert not security.verify_password("anything", "not-a-hash")


def test_token_round_trip_carries_user_id_and_role():
    payload = security.decode_access_token(security.create_access_token(42, "ADMIN"))
    assert payload["sub"] == "42"
    assert payload["role"] == "ADMIN"
    assert payload["exp"] > payload["iat"]


def test_expired_token_is_rejected():
    token = security.create_access_token(1, "CITIZEN", minutes=-1)
    with pytest.raises(security.TokenError, match="expired"):
        security.decode_access_token(token)


def test_tampered_token_is_rejected():
    token = security.create_access_token(1, "CITIZEN")
    header, payload, signature = token.split(".")
    forged = ".".join((header, payload, ("A" if signature[0] != "A" else "B") + signature[1:]))
    with pytest.raises(security.TokenError):
        security.decode_access_token(forged)


def test_token_signed_with_another_secret_is_rejected():
    token = jwt.encode({"sub": "1", "role": "ADMIN", "exp": 9_999_999_999}, "another-secret-" * 4, algorithm="HS256")
    with pytest.raises(security.TokenError):
        security.decode_access_token(token)


def test_token_without_expiry_is_rejected():
    token = jwt.encode({"sub": "1", "role": "ADMIN"}, security.signing_secret(), algorithm="HS256")
    with pytest.raises(security.TokenError):
        security.decode_access_token(token)


def test_short_jwt_secret_is_refused(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "too-short")
    with pytest.raises(RuntimeError, match="at least 32"):
        security.signing_secret()
