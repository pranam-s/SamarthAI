# Samarth AI Resume Platform

Production-oriented FastAPI platform for resume management, AI-assisted job matching, and multilingual recruiter/jobseeker workflows.

## Highlights

- FastAPI + Jinja SSR application with API + web routes.
- AI provider routing:
  - Primary: Google GenAI
  - Fallback: OpenRouter
- Secure auth improvements:
  - Password verification on login
  - Signed JWT cookies
  - CSRF checks on authenticated write forms
- Localization foundation with 20 locales (top Indian + global languages).
- Modern Python tooling:
  - `uv` dependency + lock management
  - `ruff` linting/formatting
  - `ty` type checking
  - `pytest` tests
- CI workflow with lint/type/test gates.

## Tech Stack

- Python 3.12
- FastAPI, SQLAlchemy (async), Jinja2
- SQLite (default)
- Google GenAI SDK, OpenAI SDK (for OpenRouter API compatibility)
- DaisyUI/Tailwind via CDN

## Quick Start (uv)

### 1) Install dependencies

```bash
uv sync
```

### 2) Configure environment

Create `.env`:

```env
SECRET_KEY=replace-with-long-random-secret
GOOGLE_API_KEY=your_google_genai_key
OPENROUTER_API_KEY=your_openrouter_key
GOOGLE_MODEL=gemini-2.5-flash
OPENROUTER_MODEL=openai/gpt-5.2
AI_PRIMARY_PROVIDER=google
AI_FALLBACK_PROVIDER=openrouter
APP_URL=http://localhost:8000
COOKIE_SECURE=false
```

### 3) Run app

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open:

- UI: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## Quality Commands

```bash
uv run ruff check .
uv run ty check .
uv run pytest
```

## Docker

```bash
docker compose up --build
```

## Project Structure

- `main.py` — app bootstrap
- `api.py` — API routes (`/api/v1/*`)
- `ui.py` — SSR pages
- `services.py` — AI and domain service layer
- `core/config.py` — settings and environment config
- `core/security.py` — JWT/password/CSRF helpers
- `core/i18n.py` — locale normalization + translations
- `templates/` — Jinja templates
- `tests/` — security/i18n/service fallback tests

## Localization

Locale can be switched from the sidebar language selector. Current i18n setup supports:

- Indian/region set: `en`, `hi`, `bn`, `te`, `mr`, `ta`, `ur`, `gu`, `kn`, `ml`
- Global set: `es`, `fr`, `ar`, `zh`, `pt`, `de`, `ru`, `ja`, `ko`, `it`

## Notes

- When provider keys are unavailable, service-level fallback logic keeps core flows operational.
- SQLite is default for fast local setup; production DB migration can be added in a follow-up.
