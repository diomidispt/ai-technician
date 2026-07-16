"""Unit tests for password hashing + JWT (no DB or Ollama needed)."""

import jwt
import pytest

from app.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    h = hash_password("s3cret-pw")
    assert h != "s3cret-pw"  # stored hashed, never plaintext
    assert verify_password("s3cret-pw", h)
    assert not verify_password("wrong", h)


def test_jwt_roundtrip_carries_role():
    token = create_access_token(user_id=7, email="tech@jensen.local", role="technician")
    claims = decode_access_token(token)
    assert claims["sub"] == "7"
    assert claims["email"] == "tech@jensen.local"
    assert claims["role"] == "technician"


def test_jwt_rejects_tampered_token():
    token = create_access_token(user_id=1, email="a@b.c", role="admin")
    with pytest.raises(jwt.PyJWTError):
        decode_access_token(token + "tampered")
