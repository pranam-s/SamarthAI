# agents.md

## Purpose

Defines how AI coding agents should contribute to this repository safely and consistently.

## Architecture

- **Runtime**: Python 3.12, FastAPI, SQLAlchemy 2.0 async (SQLite default / PostgreSQL production)
- **Auth**: bcrypt (direct, no passlib) + python-jose JWT + itsdangerous CSRF
- **AI**: Google GenAI (Gemini 2.5 Flash, thinking budget 8192) primary; OpenRouter fallback; heuristic fallback when keys absent
- **Frontend**: DaisyUI 3 + Tailwind CSS CDN + Alpine.js 3 + Chart.js — served via Jinja2 SSR
- **Package manager**: `uv` exclusively — do not use `pip` directly
- **Key files**: `api.py` (REST), `ui.py` (SSR routes), `services.py` (AI + domain logic), `schemas.py` (Pydantic), `models.py` (ORM), `core/` (config, security, i18n)

## Standards

- Prefer minimal, root-cause fixes over surface patches.
- Keep architecture simple: FastAPI + Jinja SSR + service layer.
- Maintain Python 3.12 compatibility.
- Use `uv` for dependency and environment management.
- Schema fields should match model nullability — nullable ORM columns must have `= None` or `= default` in Pydantic schemas.
- Run full quality gates before declaring completion (see below).

## Quality Gates (run in order)

```bash
uv run ruff format --check .   # must produce 0 differences
uv run ruff check .            # must produce 0 diagnostics
uv run ty check .              # must produce 0 diagnostics
uv run pytest tests/ -v        # all tests must pass (currently 113)
```

If any gate fails, fix the issue before committing.

## Security Rules

- Never log secrets, tokens, or passwords.
- Preserve secure auth behavior: `httponly=True` cookies, `COOKIE_SECURE` from settings, `COOKIE_SAMESITE` from settings, CSRF tokens on all authenticated form POST routes.
- API endpoints use Bearer token auth; UI routes use cookie auth + CSRF.
- Keep environment-specific settings in `.env` and `core/config.py`. Never hardcode secrets.
- CORS origins come from `settings.CORS_ORIGINS` — never use `"*"` in production.

## i18n and Accessibility

- All user-facing strings must use the `t(key)` template helper (backed by `core/i18n.py`).
- When adding new UI strings, add the key to `EN_TRANSLATIONS` first, then add translations to all 19 `LOCALE_OVERRIDES` entries (hi, bn, te, mr, ta, ur, gu, kn, ml, es, fr, ar, zh, pt, de, ru, ja, ko, it).
- The `translate()` function falls back to English for missing keys, so partial translations degrade gracefully.
- Prefer semantic HTML: use `<button>`, `<label>`, `<nav>`, `<main>`, `<section>` over generic divs.
- Decorative SVGs must have `aria-hidden="true"`.
- Forms must have accessible `<label>` elements and visible submit controls.
- Ensure keyboard navigation works (focus rings, skip-to-content link).

## AI Integrations

- Primary provider: Google GenAI (`google-genai` SDK).
- Fallback provider: OpenRouter (via `openai` SDK compatibility).
- AI prompt templates live in `prompts/*.md` — edit them there, not inline in Python.
- `AIService.parse_json()` handles JSON extraction from LLM output robustly.
- Always implement heuristic fallback paths in services so the platform works without API keys.

## Contribution Flow

1. Read all impacted files before making changes.
2. Update service and route contracts together — never change one without the other.
3. Update Pydantic schemas when ORM model fields change.
4. Update templates when endpoint or form behavior changes.
5. Add/update tests for new endpoints or business logic.
6. Add i18n keys to EN + all 19 locale overrides.
7. Run all quality gates.
8. Update `README.md` if behavior, API surface, or test count changes.

## Testing Conventions

- Use `AsyncClient` from `httpx` with `ASGITransport` for API tests.
- In-memory SQLite (`sqlite+aiosqlite:///:memory:`) for test isolation.
- Helper: `_register_and_login(client, email, password, is_recruiter)` returns auth headers.
- Test files: `tests/test_api.py`, `tests/test_services.py`, `tests/test_security.py`, `tests/test_i18n.py`.
- All tests are async (`@pytest.mark.asyncio`).

## Docker

- Base image: `python:3.12-slim` with `ghcr.io/astral-sh/uv:latest` for install.
- Non-root user `appuser` in container.
- Health check: `curl -f http://localhost:8000/` with 30s interval.
- Named volumes: `uploads_data`, `db_data` — do not use anonymous volumes.
- Resource limits: 512 MB RAM, 1.0 CPU.
- Secrets via `env_file: .env` — never bake secrets into the image.
