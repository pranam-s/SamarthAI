# agents.md

## Project (3 lines)

Samarth AI: FastAPI + Jinja SSR platform for resume management and AI-assisted
job matching (parse, score, gap analysis) for job seekers and recruiters.
SQLAlchemy 2.0 async over SQLite (default) or PostgreSQL; AI via Google GenAI
with OpenRouter fallback and heuristic fallbacks when no keys. Python 3.12, uv exclusively.

## Architecture boundaries

- `api.py` (REST `/api/v1`) and `ui.py` (SSR) → `services.py` (domain + AI) → `models.py` (ORM) → `db/database.py`.
- `schemas.py` = all Pydantic I/O contracts; `core/` = config, security, ratelimit, revocation, i18n; `prompts/*.md` = AI prompt templates (edit there, not in Python).
- Route modules: auth, permission checks, validation, response shaping only — no SQL, no AI calls.
- Style guides: `docs/style-guides/python.md`, `docs/style-guides/fastapi.md`, `docs/style-guides/testing.md` — binding summaries of PEP 8 / FastAPI / pytest conventions.

## Standards

- Minimal, root-cause fixes; no surface patches, hacks, or stubs-as-done.
- Schema nullability mirrors ORM (`= None` on nullable columns).
- Update routes + services + schemas + templates together; add i18n keys to EN + all 19 locale overrides.
- Quality gates before every commit: `uv run ruff format --check . && uv run ruff check . && uv run ty check && uv run pytest tests/`.
- Conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `chore(deps):`, `ci:`); commit after each green step.

## Testing policy

- pytest + pytest-asyncio (auto mode) + httpx ASGITransport; in-memory SQLite per test.
- Test behavior and both sides of permission checks; exercise heuristic fallbacks by disabling provider clients, never by monkeypatching privates.
- CI gates ≥95% coverage on `core/`, `db/`, `models.py`, `schemas.py` (measured 100%); `api/services/ui` reported only — coverage.py undercounts post-await code (docs/EVALUATION.md).

## Security rules

- Never log secrets/tokens/passwords; never render raw exception text to users.
- httponly cookies, `COOKIE_SECURE`/`COOKIE_SAMESITE` from settings, CSRF on every authenticated form POST; Bearer auth on the API.
- bcrypt direct (no passlib); PyJWT HS256 (`sub` as str, int-parsed at the boundary); itsdangerous CSRF.
- Redirect targets from user input must be same-origin relative paths.
- Uploads: `.pdf`/`.docx`/`.txt` only, capped at `MAX_UPLOAD_SIZE`.
- Secrets only via `.env` (see `.env.example`); CORS from settings, never `*` in production.

## Accessibility (SSR UI)

- Semantic HTML (`button`, `label`, `nav`, `main`); decorative SVGs get `aria-hidden="true"`.
- Keyboard-navigable throughout: visible focus rings, skip-to-content link, no mouse-only interactions.
- All user-facing strings via the `t(key)` helper (`core/i18n.py`).

## AI integrations

- Google GenAI primary (Gemini 2.5 Flash, `GOOGLE_THINKING_BUDGET`), OpenRouter fallback, heuristic fallbacks so core flows work keyless.
- `AIService.parse_json()` extracts JSON from LLM output; prompts externalized in `prompts/*.md`.

## Docker

- `python:3.12-slim`, non-root `appuser`, healthcheck on `/`, named volumes `uploads_data`/`db_data`, 512 MB / 1 CPU limits, secrets via `env_file`.
