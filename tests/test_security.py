"""Tests for core/security.py – JWT, password hashing, CSRF."""

from __future__ import annotations

import time
from datetime import timedelta

from core.security import (
    create_access_token,
    create_csrf_token,
    decode_access_token,
    get_password_hash,
    verify_csrf_token,
    verify_password,
)

# ---------------------------------------------------------------------------
# JWT access tokens
# ---------------------------------------------------------------------------


class TestAccessToken:
    def test_roundtrip(self) -> None:
        token = create_access_token(subject=123, expires_delta=timedelta(minutes=5))
        payload = decode_access_token(token)
        assert payload["sub"] == "123"
        assert "exp" in payload

    def test_string_subject(self) -> None:
        token = create_access_token(subject="user@example.com", expires_delta=timedelta(minutes=5))
        payload = decode_access_token(token)
        assert payload["sub"] == "user@example.com"

    def test_default_expiry(self) -> None:
        token = create_access_token(subject=1)
        payload = decode_access_token(token)
        assert "exp" in payload
        assert payload["exp"] > time.time()

    def test_expired_token_raises(self) -> None:
        import jwt as pyjwt
        import pytest

        token = create_access_token(subject=1, expires_delta=timedelta(seconds=-1))
        with pytest.raises(pyjwt.ExpiredSignatureError):
            decode_access_token(token)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------


class TestPasswordHashing:
    def test_hash_and_verify(self) -> None:
        password = "super-secret-123!"
        hashed = get_password_hash(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password_fails(self) -> None:
        hashed = get_password_hash("correct-password")
        assert verify_password("wrong-password", hashed) is False

    def test_unique_hashes(self) -> None:
        h1 = get_password_hash("same-password")
        h2 = get_password_hash("same-password")
        assert h1 != h2  # bcrypt uses random salt


# ---------------------------------------------------------------------------
# CSRF tokens
# ---------------------------------------------------------------------------


class TestCSRFToken:
    def test_validation(self) -> None:
        token = create_csrf_token(subject=42)
        assert verify_csrf_token(token, subject=42) is True
        assert verify_csrf_token(token, subject=99) is False

    def test_tamper_fails(self) -> None:
        token = create_csrf_token(subject=7)
        tampered = f"{token}x"
        assert verify_csrf_token(tampered, subject=7) is False

    def test_empty_token_fails(self) -> None:
        assert verify_csrf_token("", subject=1) is False

    def test_integer_and_string_subjects(self) -> None:
        token = create_csrf_token(subject="user-abc")
        assert verify_csrf_token(token, subject="user-abc") is True
        assert verify_csrf_token(token, subject="user-xyz") is False
