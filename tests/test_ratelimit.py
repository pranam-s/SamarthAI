"""Tests for core/ratelimit.py and login rate limiting on POST /api/v1/auth/login."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from httpx import AsyncClient

from core.ratelimit import SlidingWindowLimiter, _monotonic, login_limiter


class FakeClock:
    """Deterministic monotonic-style clock for deterministic limiter tests."""

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
def limiter(clock: FakeClock) -> SlidingWindowLimiter:
    return SlidingWindowLimiter(max_attempts=3, window_seconds=60, clock=clock)


@pytest.fixture(autouse=True)
def _clean_login_limiter() -> Iterator[None]:
    login_limiter.reset_all()
    yield
    login_limiter.reset_all()


class TestSlidingWindowLimiter:
    def test_allows_up_to_limit_then_blocks(self, limiter: SlidingWindowLimiter) -> None:
        assert limiter.hit("k") is None
        assert limiter.hit("k") is None
        assert limiter.hit("k") is None
        assert limiter.hit("k") == 60

    def test_window_expiry_reallows_and_resets_history(
        self, limiter: SlidingWindowLimiter, clock: FakeClock
    ) -> None:
        for _ in range(3):
            assert limiter.hit("k") is None
        assert limiter.hit("k") == 60

        clock.advance(60)
        assert limiter.hit("k") is None

    def test_blocked_attempts_do_not_delay_expiry(
        self, limiter: SlidingWindowLimiter, clock: FakeClock
    ) -> None:
        for _ in range(3):
            limiter.hit("k")
        clock.advance(30)
        for _ in range(10):
            assert limiter.hit("k") == 30
        clock.advance(30)
        assert limiter.hit("k") is None

    def test_keys_are_isolated(self, limiter: SlidingWindowLimiter) -> None:
        for _ in range(3):
            limiter.hit("a")
        assert limiter.hit("a") == 60
        assert limiter.hit("b") is None

    def test_retry_after_counts_down_from_oldest_attempt(
        self, limiter: SlidingWindowLimiter, clock: FakeClock
    ) -> None:
        limiter.hit("k")
        clock.advance(20)
        for _ in range(2):
            limiter.hit("k")
        clock.advance(15)
        assert limiter.hit("k") == 25

    def test_reset_clears_one_key(self, limiter: SlidingWindowLimiter) -> None:
        for _ in range(3):
            limiter.hit("a")
        limiter.reset("a")
        assert limiter.hit("a") is None
        assert limiter.hit("b") is None

    def test_reset_all_clears_every_key(self, limiter: SlidingWindowLimiter) -> None:
        for _ in range(3):
            limiter.hit("a")
            limiter.hit("b")
        limiter.reset_all()
        assert limiter.hit("a") is None
        assert limiter.hit("b") is None

    def test_periodic_sweep_drops_expired_keys(
        self, limiter: SlidingWindowLimiter, clock: FakeClock
    ) -> None:
        limiter.hit("hot")
        for i in range(126):
            limiter.hit(f"churn{i}")
        clock.advance(61)  # every record above is now expired
        limiter.hit("trigger")  # 128th hit: the sweep drops the expired keys
        assert limiter.hit("trigger") is None
        assert limiter.hit("hot") is None

    def test_default_clock_is_monotonic_time(self) -> None:
        assert isinstance(_monotonic(), float)


async def _register(client: AsyncClient, email: str) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-pass", "full_name": "RL User"},
    )


class TestLoginRateLimitAPI:
    async def test_login_blocked_after_max_attempts(self, client: AsyncClient) -> None:
        email = "rl-block@example.com"
        await _register(client, email)

        for _ in range(5):
            resp = await client.post(
                "/api/v1/auth/login", data={"username": email, "password": "wrong"}
            )
            assert resp.status_code == 401

        resp = await client.post(
            "/api/v1/auth/login", data={"username": email, "password": "wrong"}
        )
        assert resp.status_code == 429
        assert "Too many login attempts" in resp.json()["detail"]
        retry_after = resp.headers["Retry-After"]
        assert retry_after.isdigit() and 1 <= int(retry_after) <= 300

    async def test_rate_limited_even_with_correct_password(self, client: AsyncClient) -> None:
        email = "rl-correct@example.com"
        await _register(client, email)

        for _ in range(5):
            await client.post("/api/v1/auth/login", data={"username": email, "password": "wrong"})

        resp = await client.post(
            "/api/v1/auth/login", data={"username": email, "password": "correct-pass"}
        )
        assert resp.status_code == 429

    async def test_limit_is_per_username(self, client: AsyncClient) -> None:
        exhausted = "rl-exhausted@example.com"
        other = "rl-other@example.com"
        await _register(client, exhausted)
        await _register(client, other)

        for _ in range(5):
            await client.post(
                "/api/v1/auth/login", data={"username": exhausted, "password": "wrong"}
            )
        assert (
            await client.post(
                "/api/v1/auth/login", data={"username": exhausted, "password": "wrong"}
            )
        ).status_code == 429

        resp = await client.post(
            "/api/v1/auth/login", data={"username": other, "password": "correct-pass"}
        )
        assert resp.status_code == 200
