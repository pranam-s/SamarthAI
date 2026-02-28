from datetime import timedelta

from core.security import (
    create_access_token,
    create_csrf_token,
    decode_access_token,
    verify_csrf_token,
)


def test_access_token_roundtrip() -> None:
    token = create_access_token(subject=123, expires_delta=timedelta(minutes=5))
    payload = decode_access_token(token)
    assert payload["sub"] == "123"
    assert "exp" in payload


def test_csrf_token_validation() -> None:
    token = create_csrf_token(subject=42)
    assert verify_csrf_token(token, subject=42) is True
    assert verify_csrf_token(token, subject=99) is False
