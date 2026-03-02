# Samarth AI Resume Platform

Production-oriented FastAPI platform for resume management, AI-assisted job matching, skills gap analysis, and multilingual recruiter/jobseeker workflows.

**Maintainer:** pranam-s · [GitHub](https://github.com/pranam-s/SamarthAI)

## Highlights

- **FastAPI + Jinja SSR** — REST API + server-rendered UI, unified codebase.
- **AI provider routing** with graceful degradation:
  - Primary: Google GenAI (Gemini 2.5 Flash with thinking budget)
  - Fallback: OpenRouter (OpenAI-compatible)
  - Heuristic fallbacks when both providers are unavailable
- **Externalized AI prompts** in Markdown files (`prompts/`) — edit without touching Python.
- **Secure authentication**:
  - bcrypt password hashing (direct, no passlib)
  - Signed JWT access tokens with configurable expiry
  - CSRF protection on all authenticated write forms
  - HTTP-only secure cookies with configurable `SameSite`
- **Skills Gap Analysis** — compare resume skills to job requirements, get a gap score and learning path.
- **Job management** — post, edit, and delete jobs (recruiters); browse and apply (job seekers).
- **Localization** — 20 locales (10 Indian + 10 global), fully translated including new features.
- **Modern Python tooling** — `uv`, `ruff`, `ty`, `pytest`, GitHub Actions CI.
- **Docker ready** — compose with named volumes, health check, and resource limits.

## Tech Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.12 |
| Web Framework | FastAPI + Jinja2 SSR |
| ORM | SQLAlchemy 2.0 (async) |
| Database | SQLite (default) / PostgreSQL (asyncpg) |
| AI Primary | Google GenAI SDK — Gemini 2.5 Flash |
| AI Fallback | OpenAI SDK → OpenRouter |
| Auth | bcrypt + python-jose JWT + itsdangerous CSRF |
| Frontend | DaisyUI 3 + Tailwind CSS CDN + Alpine.js + Chart.js |
| Testing | pytest + pytest-asyncio + httpx AsyncClient |
| Linting | ruff (format + check) |
| Type Checking | ty |
| Package Manager | uv |

## Features

### Job Seekers

- Upload resume (PDF, DOCX, TXT) or paste plain text
- AI resume parsing: skills, experience, education, projects, certifications
- Browse and apply to jobs with AI-computed match scores
- AI resume improvement suggestions and quality scoring
- **Skills Gap Analysis**: gap score, matched/missing skills, personalized learning path
- Application tracking with status updates

### Recruiters

- Post, edit, and delete job listings
- Review applications with AI match details and structured feedback
- Update application status (new → reviewed → shortlisted → rejected)
- Market analysis: skill demand charts, top skills, job counts

## Quick Start

### 1. Install dependencies

```bash
uv sync
```

### 2. Configure environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Key variables:

```env
SECRET_KEY=replace-with-long-random-secret
GOOGLE_API_KEY=your_google_genai_key
OPENROUTER_API_KEY=your_openrouter_key
DATABASE_URL=sqlite+aiosqlite:///./job_matcher.db
COOKIE_SECURE=false
```

### 3. Run the app

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- **UI:** <http://localhost:8000>
- **API docs:** <http://localhost:8000/api/v1/docs>

## API Overview

All API endpoints are prefixed with `/api/v1/`.

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Register user |
| POST | `/auth/login` | Login, returns JWT |
| GET | `/auth/me` | Current user info |
| POST | `/resumes/` | Create resume from text |
| GET | `/resumes/` | List resumes |
| GET | `/resumes/{id}` | Get resume |
| DELETE | `/resumes/{id}` | Delete resume |
| POST | `/resumes/upload` | Upload resume file (multipart) |
| POST | `/resumes/upload-base64` | Upload base64-encoded resume |
| POST | `/resumes/{id}/improve` | AI improvement suggestions |
| GET | `/resumes/{id}/quality-score` | AI quality score |
| POST | `/jobs/` | Create job posting |
| GET | `/jobs/` | List jobs |
| GET | `/jobs/{id}` | Get job |
| PUT | `/jobs/{id}` | Update job |
| DELETE | `/jobs/{id}` | Delete job |
| POST | `/match` | Match resume to job |
| POST | `/applications/` | Apply to job |
| GET | `/applications/` | List applications |
| GET | `/applications/{id}` | Get application detail |
| PATCH | `/applications/{id}/status` | Update application status |
| GET | `/recommendations` | Personalized job recommendations |
| GET | `/market-analysis` | Market skill demand analysis |
| POST | `/skills-gap` | Skills gap analysis |

## Quality Gates

```bash
uv run ruff format --check .   # formatting
uv run ruff check .            # linting
uv run ty check .              # type checking
uv run pytest tests/ -v        # 113 tests
```

## Docker

```bash
docker compose up --build
```

The compose file includes a health check, named volumes for uploads and the database, and resource limits (512 MB RAM, 1 CPU).

## Project Structure

```text
├── main.py              App bootstrap & lifespan
├── api.py               REST API routes (/api/v1/*)
├── ui.py                Server-rendered UI routes
├── services.py          AI + domain service layer
├── models.py            SQLAlchemy ORM models
├── schemas.py           Pydantic request/response schemas
├── core/
│   ├── config.py        Settings & environment config
│   ├── security.py      bcrypt / JWT / CSRF helpers
│   └── i18n.py          Locale normalization + 20-locale translations
├── db/
│   └── database.py      Async engine & session factory
├── prompts/             Externalized AI prompt templates (.md)
├── templates/           Jinja2 SSR templates
├── static/              Static assets
├── tests/               113 tests (services, security, i18n, API)
├── .env.example         Example environment configuration
├── .github/workflows/   CI/CD pipeline (quality + test + docker)
├── Dockerfile           Container build (python:3.12-slim, non-root user)
└── docker-compose.yml   Compose orchestration with health check
```

## Localization

Locale is switched from the sidebar language selector (persisted in a cookie).

| Group | Locales |
|---|---|
| Indian / Regional | `en`, `hi`, `bn`, `te`, `mr`, `ta`, `ur`, `gu`, `kn`, `ml` |
| Global | `es`, `fr`, `ar`, `zh`, `pt`, `de`, `ru`, `ja`, `ko`, `it` |

All UI strings — including Skills Gap Analysis and Job Edit/Delete — are fully translated across all 20 locales. English is the base; other locales inherit any untranslated keys automatically.

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | (random) | JWT signing key — **set in production** |
| `GOOGLE_API_KEY` | — | Google GenAI API key |
| `OPENROUTER_API_KEY` | — | OpenRouter API key (fallback) |
| `DATABASE_URL` | SQLite | Async SQLAlchemy URL |
| `COOKIE_SECURE` | `false` | Set `true` in production (HTTPS) |
| `CORS_ORIGINS` | localhost | Comma-separated allowed origins |
| `DEFAULT_LOCALE` | `en` | Default UI locale |
| `AI_THINKING_BUDGET` | `8192` | Gemini thinking token budget |

## Notes

- When AI provider keys are unavailable, heuristic fallbacks keep all core flows operational.
- SQLite is the default for fast local setup; switch to PostgreSQL via `DATABASE_URL=postgresql+asyncpg://...`.
- AI prompts live in `prompts/*.md` — edit them without touching Python code.
- All form writes are CSRF-protected; the API uses Bearer token auth separately.


## Highlights

- **FastAPI + Jinja SSR** application with API + web routes.
- **AI provider routing** with graceful degradation:
  - Primary: Google GenAI (Gemini 2.5 Flash with thinking budget)
  - Fallback: OpenRouter
  - Heuristic fallbacks when both providers are unavailable
- **Externalized AI prompts** in Markdown files (`prompts/`) for easy editing.
- **Secure authentication**:
  - bcrypt password hashing (direct, no passlib)
  - Signed JWT access tokens with configurable expiry
  - CSRF protection on authenticated write forms
  - HTTP-only secure cookies
- **Localization** with 20 locales (Indian + global languages).
- **Modern Python tooling**:
  - `uv` dependency + lock management
  - `ruff` linting/formatting
  - `ty` type checking
  - `pytest` with 96 tests and async support
- **CI/CD** with GitHub Actions (quality, test, Docker build).
- **Docker** ready with compose support.

## Tech Stack

| Layer | Technology |
| ----- | --------- |
| Runtime | Python 3.12 |
| Web Framework | FastAPI + Jinja2 SSR |
| ORM | SQLAlchemy 2.0 (async) |
| Database | SQLite (default) / PostgreSQL (asyncpg) |
| AI Primary | Google GenAI SDK (Gemini 2.5 Flash) |
| AI Fallback | OpenAI SDK → OpenRouter |
| Auth | bcrypt + python-jose JWT + itsdangerous CSRF |
| Frontend | DaisyUI 3 + Tailwind CSS + Alpine.js + Chart.js |
| Testing | pytest + pytest-asyncio + httpx |
| Linting | ruff (format + check) |
| Type Checking | ty |
| Package Mgr | uv |

## Quick Start

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
OPENROUTER_MODEL=google/gemini-2.5-flash
AI_PRIMARY_PROVIDER=google
AI_FALLBACK_PROVIDER=openrouter
GOOGLE_THINKING_BUDGET=8192
APP_URL=http://localhost:8000
COOKIE_SECURE=false
```

### 3) Run the app

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

- UI: <http://localhost:8000>
- API docs: <http://localhost:8000/docs>

## Quality Gates

```bash
uv run ruff format --check .   # formatting
uv run ruff check .            # linting
uv run ty check                # type checking
uv run pytest tests/ -v        # 96 tests
```

## Docker

```bash
docker compose up --build
```

## Project Structure

```text
├── main.py              App bootstrap & lifespan
├── api.py               REST API routes (/api/v1/*)
├── ui.py                Server-rendered pages
├── services.py          AI + domain service layer
├── models.py            SQLAlchemy ORM models
├── schemas.py           Pydantic request/response schemas
├── core/
│   ├── config.py        Settings & environment config
│   ├── security.py      bcrypt / JWT / CSRF helpers
│   └── i18n.py          Locale normalization + 20-locale translations
├── db/
│   └── database.py      Async engine & session factory
├── prompts/             Externalized AI prompt templates (.md)
├── templates/           Jinja2 SSR templates
├── static/              Static assets
├── tests/               96 tests (services, security, i18n, API, schemas)
├── .github/workflows/   CI/CD pipeline
├── Dockerfile           Container build
└── docker-compose.yml   Compose orchestration
```

## Localization

Locale can be switched from the sidebar language selector. Supported locales:

- **Indian / Regional**: `en`, `hi`, `bn`, `te`, `mr`, `ta`, `ur`, `gu`, `kn`, `ml`
- **Global**: `es`, `fr`, `ar`, `zh`, `pt`, `de`, `ru`, `ja`, `ko`, `it`

English is the base; other locales inherit missing translations from English automatically.

## Notes

- When AI provider keys are unavailable, heuristic fallbacks keep all core flows operational.
- SQLite is the default for fast local setup; switch to PostgreSQL by setting `DATABASE_URL`.
- AI prompts live in `prompts/*.md` — edit them without touching Python code.
