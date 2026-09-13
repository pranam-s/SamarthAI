"""Tests for core/revocation.py and the JWT revocation story (jti denylist + logout)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient

from core.config import settings
from core.revocation import TokenDenylist, token_denylist
from core.security import (
    ALGORITHM,
    create_access_token,
    decode_access_token,
    decode_token_subject,
    revoke_token,
)


class FakeClock:
    """Deterministic wall-clock for deterministic denylist tests."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def denylist(clock: FakeClock) -> TokenDenylist:
    return TokenDenylist(clock=clock)


@pytest.fixture(autouse=True)
def _clean_token_denylist() -> Iterator[None]:
    token_denylist.reset_all()
    yield
    token_denylist.reset_all()


class TestTokenDenylist:
    def test_revoked_jti_is_reported(self, denylist: TokenDenylist, clock: FakeClock) -> None:
        denylist.revoke("j1", exp=clock.now + 60)
        assert denylist.is_revoked("j1") is True
        assert denylist.is_revoked("j2") is False

    def test_entry_expires_with_the_token(self, denylist: TokenDenylist, clock: FakeClock) -> None:
        denylist.revoke("j1", exp=clock.now + 60)
        clock.advance(60)
        assert denylist.is_revoked("j1") is False
        assert denylist.is_revoked("j1") is False

    def test_purge_on_revoke_drops_expired_entries(
        self, denylist: TokenDenylist, clock: FakeClock
    ) -> None:
        denylist.revoke("old", exp=clock.now + 10)
        clock.advance(11)
        denylist.revoke("new", exp=clock.now + 60)
        assert denylist.is_revoked("old") is False
        assert denylist.is_revoked("new") is True

    def test_reset_all_clears_entries(self, denylist: TokenDenylist, clock: FakeClock) -> None:
        denylist.revoke("j1", exp=clock.now + 60)
        denylist.reset_all()
        assert denylist.is_revoked("j1") is False


class TestTokenRevocation:
    def test_tokens_carry_jti(self) -> None:
        payload = decode_access_token(create_access_token(subject=1))
        assert isinstance(payload["jti"], str)
        assert payload["jti"]

    def test_revoked_token_rejected_by_decode(self) -> None:
        token = create_access_token(subject=1)
        assert decode_token_subject(token) == "1"
        assert revoke_token(token) is True
        assert decode_token_subject(token) is None

    def test_unrevoked_token_still_decodes(self) -> None:
        token = create_access_token(subject=7)
        assert decode_token_subject(token) == "7"

    def test_revoke_accepts_bearer_prefix(self) -> None:
        token = create_access_token(subject=1)
        assert revoke_token(f"Bearer {token}") is True
        assert decode_token_subject(token) is None

    def test_revoke_rejects_garbage(self) -> None:
        assert revoke_token("garbage.token.value") is False

    def test_legacy_token_without_jti_decodes_but_cannot_be_revoked(self) -> None:
        legacy = jwt.encode(
            {"sub": "5", "exp": datetime.now(UTC) + timedelta(minutes=5)},
            settings.SECRET_KEY,
            algorithm=ALGORITHM,
        )
        assert decode_token_subject(legacy) == "5"
        assert revoke_token(legacy) is False


class TestAPILogout:
    async def test_logout_revokes_token_for_remaining_lifetime(self, client: AsyncClient) -> None:
        await client.post(
            "/api/v1/auth/register",
            json={"email": "logout@example.com", "password": "correct-pass", "full_name": "LO"},
        )
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "logout@example.com", "password": "correct-pass"},
        )
        headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 200

        assert (await client.post("/api/v1/auth/logout", headers=headers)).status_code == 204
        assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 401

    async def test_logout_without_token_is_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.post("/api/v1/auth/logout")
        assert resp.status_code == 401
        assert resp.headers["WWW-Authenticate"] == "Bearer"

    async def test_logout_with_invalid_token_is_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/auth/logout", headers={"Authorization": "Bearer garbage.token.value"}
        )
        assert resp.status_code == 401


class TestUILogout:
    async def test_ui_logout_revokes_cookie_token(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/register",
            data={
                "email": "ui-logout@example.com",
                "full_name": "UI LO",
                "password": "correct-pass",
                "is_recruiter": "false",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        resp = await client.post(
            "/login",
            data={"email": "ui-logout@example.com", "password": "correct-pass"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert (await client.get("/dashboard", follow_redirects=False)).status_code == 200

        old_token = client.cookies[settings.AUTH_COOKIE_NAME]
        assert (await client.get("/logout", follow_redirects=False)).status_code == 303

        client.cookies.set(settings.AUTH_COOKIE_NAME, old_token)
        assert (await client.get("/dashboard", follow_redirects=False)).status_code in (303, 401)
