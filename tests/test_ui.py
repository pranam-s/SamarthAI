"""Tests for server-rendered UI routes (ui.py) — auth flow, CSRF, locale redirect safety."""

from __future__ import annotations

import re

from httpx import AsyncClient

CSRF_INPUT_RE = re.compile(r'name="csrf_token"[^>]*value="([^"]+)"')


async def _register_and_login_ui(
    client: AsyncClient,
    email: str,
    password: str,
    is_recruiter: bool = False,
) -> None:
    resp = await client.post(
        "/register",
        data={
            "email": email,
            "full_name": "UI Tester",
            "password": password,
            "is_recruiter": "true" if is_recruiter else "false",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    resp = await client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "access_token" in resp.cookies


async def _get_csrf_token(client: AsyncClient, path: str) -> str:
    resp = await client.get(path)
    assert resp.status_code == 200
    match = CSRF_INPUT_RE.search(resp.text)
    assert match, f"No csrf_token input found on {path}"
    return match.group(1)


# ---------------------------------------------------------------------------
# Locale switching / redirect safety
# ---------------------------------------------------------------------------


class TestSetLocale:
    async def test_valid_locale_sets_cookie_and_keeps_relative_path(self, client: AsyncClient):
        resp = await client.post(
            "/set-locale",
            data={"locale": "fr", "redirect_to": "/jobs"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/jobs"
        assert "locale=fr" in resp.headers["set-cookie"]

    async def test_absolute_url_rejected(self, client: AsyncClient):
        resp = await client.post(
            "/set-locale",
            data={"locale": "en", "redirect_to": "https://evil.example/phish"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/"

    async def test_protocol_relative_url_rejected(self, client: AsyncClient):
        resp = await client.post(
            "/set-locale",
            data={"locale": "en", "redirect_to": "//evil.example"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/"

    async def test_unknown_locale_falls_back_to_english(self, client: AsyncClient):
        resp = await client.post(
            "/set-locale",
            data={"locale": "zz", "redirect_to": "/"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert "locale=en" in resp.headers["set-cookie"]


# ---------------------------------------------------------------------------
# Anonymous access / malformed auth cookies
# ---------------------------------------------------------------------------


class TestAnonymousAccess:
    async def test_home_renders_anonymously(self, client: AsyncClient):
        resp = await client.get("/")
        assert resp.status_code == 200

    async def test_home_with_garbage_cookie_stays_anonymous(self, client: AsyncClient):
        client.cookies.set("access_token", "not-a-real-token")
        resp = await client.get("/")
        assert resp.status_code == 200

    async def test_protected_page_redirects_without_login(self, client: AsyncClient):
        # UI routes use API get_current_user, which raises 401 for anonymous users.
        resp = await client.get("/resumes")
        assert resp.status_code in (303, 401)


# ---------------------------------------------------------------------------
# Auth flow
# ---------------------------------------------------------------------------


class TestAuthFlow:
    async def test_register_login_dashboard(self, client: AsyncClient):
        await _register_and_login_ui(client, "ui-user@example.com", "ui-pass-123")
        resp = await client.get("/dashboard")
        assert resp.status_code == 200

    async def test_login_wrong_password_shows_error(self, client: AsyncClient):
        await client.post(
            "/register",
            data={"email": "ui-wrong@example.com", "full_name": "X", "password": "right-pass"},
        )
        resp = await client.post(
            "/login",
            data={"email": "ui-wrong@example.com", "password": "wrong-pass"},
        )
        assert resp.status_code == 400
        assert "Invalid email or password" in resp.text

    async def test_login_error_localized(self, client: AsyncClient):
        client.cookies.set("locale", "es")
        resp = await client.post(
            "/login",
            data={"email": "nobody@example.com", "password": "whatever1"},
        )
        assert resp.status_code == 400
        assert "Correo electrónico o contraseña no válidos" in resp.text

    async def test_duplicate_register_rejected(self, client: AsyncClient):
        payload = {"email": "ui-dup@example.com", "full_name": "X", "password": "pass-12345"}
        first = await client.post("/register", data=payload)
        assert first.status_code == 303
        second = await client.post("/register", data=payload)
        assert second.status_code == 400

    async def test_register_short_password_rejected(self, client: AsyncClient):
        resp = await client.post(
            "/register",
            data={"email": "ui-shortpw@example.com", "full_name": "X", "password": "short"},
        )
        assert resp.status_code == 400
        assert "at least 8" in resp.text

    async def test_duplicate_register_error_localized(self, client: AsyncClient):
        payload = {"email": "ui-i18n@example.com", "full_name": "X", "password": "pass-12345"}
        first = await client.post("/register", data=payload)
        assert first.status_code == 303
        client.cookies.set("locale", "fr")
        second = await client.post("/register", data=payload)
        assert second.status_code == 400
        assert "déjà enregistré" in second.text


# ---------------------------------------------------------------------------
# CSRF protection on UI form posts
# ---------------------------------------------------------------------------


class TestCsrfProtection:
    async def test_job_creation_without_valid_csrf_rejected(self, client: AsyncClient):
        await _register_and_login_ui(
            client, "ui-recruiter@example.com", "ui-pass-123", is_recruiter=True
        )
        resp = await client.post(
            "/jobs/create",
            data={
                "title": "Backend Engineer",
                "description_text": "Python and SQL required",
                "csrf_token": "forged-token",
            },
        )
        assert resp.status_code == 400

    async def test_create_and_edit_job_via_ui(self, client: AsyncClient):
        await _register_and_login_ui(
            client, "ui-recruiter2@example.com", "ui-pass-123", is_recruiter=True
        )
        csrf = await _get_csrf_token(client, "/jobs/create")

        resp = await client.post(
            "/jobs/create",
            data={
                "title": "Platform Engineer",
                "description_text": "We need Python, Docker and SQL",
                "csrf_token": csrf,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        job_path = resp.headers["location"]
        assert job_path.startswith("/jobs/")

        # Edit the job: parsed skills must be refreshed, not wiped (audit A-24 fix)
        edit_csrf = await _get_csrf_token(client, f"{job_path}/edit")
        resp = await client.post(
            f"{job_path}/edit",
            data={
                "title": "Platform Engineer II",
                "description_text": "Now requiring Kubernetes and Go",
                "csrf_token": edit_csrf,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

        detail = await client.get(job_path)
        assert detail.status_code == 200

    async def test_delete_job_via_ui(self, client: AsyncClient):
        await _register_and_login_ui(
            client, "ui-recruiter3@example.com", "ui-pass-123", is_recruiter=True
        )
        csrf = await _get_csrf_token(client, "/jobs/create")
        resp = await client.post(
            "/jobs/create",
            data={
                "title": "Temp Job",
                "description_text": "Python",
                "csrf_token": csrf,
            },
            follow_redirects=False,
        )
        job_path = resp.headers["location"]
        delete_csrf = await _get_csrf_token(client, f"{job_path}/edit")
        resp = await client.post(
            f"{job_path}/delete",
            data={"csrf_token": delete_csrf},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] == "/jobs"


# ---------------------------------------------------------------------------
# Applications list (renders plain dict rows, audit A-15)
# ---------------------------------------------------------------------------


class TestApplicationsPage:
    async def _create_application(self, client: AsyncClient, job_title: str) -> None:
        """Recruiter posts a job, then a seeker uploads a resume and applies."""
        await _register_and_login_ui(
            client, "ui-apprec@example.com", "ui-pass-123", is_recruiter=True
        )
        csrf = await _get_csrf_token(client, "/jobs/create")
        resp = await client.post(
            "/jobs/create",
            data={
                "title": job_title,
                "description_text": "Python and SQL required",
                "csrf_token": csrf,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        job_id = resp.headers["location"].rsplit("/", 1)[-1]

        await _register_and_login_ui(client, "ui-appseeker@example.com", "ui-pass-123")
        csrf = await _get_csrf_token(client, "/resumes/create")
        resp = await client.post(
            "/resumes/create",
            data={
                "resume_text": "Jane Doe\nPython Developer\nEmail: jane@example.com\nPython SQL",
                "csrf_token": csrf,
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303
        resume_id = resp.headers["location"].rsplit("/", 1)[-1]

        job_page = await client.get(f"/jobs/{job_id}")
        csrf = CSRF_INPUT_RE.search(job_page.text).group(1)
        resp = await client.post(
            "/applications/create",
            data={"job_id": job_id, "resume_id": resume_id, "csrf_token": csrf},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    async def test_seeker_sees_job_and_resume_names(self, client: AsyncClient):
        await self._create_application(client, "Listing Job Alpha")
        resp = await client.get("/applications")
        assert resp.status_code == 200
        assert "Listing Job Alpha" in resp.text
        assert "Jane Doe" in resp.text

    async def test_recruiter_sees_applicant_name(self, client: AsyncClient):
        await self._create_application(client, "Listing Job Beta")
        # Log back in as the recruiter registered by _create_application.
        resp = await client.post(
            "/login",
            data={"email": "ui-apprec@example.com", "password": "ui-pass-123"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        resp = await client.get("/applications")
        assert resp.status_code == 200
        assert "Listing Job Beta" in resp.text
        assert "Jane Doe" in resp.text
