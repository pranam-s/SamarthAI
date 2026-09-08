# Testing Patterns (summary)

Authoritative sources: [pytest docs](https://docs.pytest.org/en/stable/contents.html) ·
[pytest-asyncio](https://pytest-asyncio.readthedocs.io/) ·
[FastAPI testing docs](https://fastapi.tiangolo.com/tutorial/testing/) ·
[coverage.py](https://coverage.readthedocs.io/)

## Stack

pytest 9 · pytest-asyncio 1.x (`asyncio_mode = "auto"`) · pytest-cov 7 ·
httpx `AsyncClient` + `ASGITransport`.

## Conventions (this repo)

- All tests async; no `@pytest.mark.asyncio` needed (auto mode).
- Fixtures in `tests/conftest.py`:
  - `client` — httpx AsyncClient with `get_db` overridden to a fresh in-memory
    SQLite session per test (create_all/drop_all around each test).
  - `sample_resume_text`, `sample_parsed_resume`, `sample_parsed_job` — shared payloads.
- API helper: `_register_and_login(client, ...)` returns Bearer headers.
- UI helper: `_register_and_login_ui(client, ...)` sets the auth cookie through
  the real form endpoints; `_get_csrf_token(client, path)` scrapes the hidden input.
- Test files mirror the module under test: `test_api.py`, `test_ui.py`,
  `test_services.py`, `test_security.py`, `test_i18n.py`, `test_schemas.py`,
  `test_core.py`.

## What to test

- Behavior, not implementation: assert on HTTP status + response body, or on
  returned domain objects — never on mocks of internals.
- Both sides of every permission check (owner vs non-owner, recruiter vs seeker).
- Fallback paths: disable both AI provider clients
  (`service.google_client = None; service.openrouter_client = None`) and assert
  the heuristic path; do not monkeypatch private methods.
- Failure modes: 401/403/404/413/415 responses, malformed tokens, invalid CSRF,
  oversize/disallowed uploads.

## Coverage policy

- CI gates ≥95% line coverage on `core/`, `db/`, `models.py`, `schemas.py`
  (pure logic, fully measurable).
- `api.py`, `services.py`, `ui.py` are **reported but not gated**: coverage.py
  (7.13–7.16, both `sysmon` and `ctrace` cores, Python 3.12 and 3.13) fails to
  record code resumed after an `await` on the aiosqlite thread. Reproduced with
  a minimal Starlette+SQLAlchemy app; see docs/EVALUATION.md. Undercounts are
  deterministic, so the reported numbers are still useful as a regression trend.
