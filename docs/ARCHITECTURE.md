# Architecture — Samarth AI

## System overview

```
Browser ──► main.py (FastAPI app)
             ├── /api/v1/*  → api.py    (REST, Bearer JWT)
             ├── /*         → ui.py     (Jinja2 SSR, session cookie + CSRF)
             ├── /static    → StaticFiles
             └── lifespan: create_all (fresh-DB convenience; ADR-0001)
                        │
                        ▼
                  services.py ──── AIService (Google GenAI → OpenRouter → heuristics)
                        │
                        ▼
                  models.py (SQLAlchemy 2.0 async ORM) ──── migrations/ (Alembic)
                        │
                        ▼
              db/database.py → aiosqlite (SQLite) / asyncpg (PostgreSQL)
```

## Modules

| Module | Responsibility | Must not contain |
|---|---|---|
| `main.py` | App factory wiring, CORS, static mount, lifespan (`create_all`, fresh DBs only — ADR-0001) | Business logic |
| `api.py` | REST routes `/api/v1/*`, `get_current_user` (JWT → user), permission checks | SQL, AI calls |
| `ui.py` | SSR routes, form handling, CSRF validation, `get_optional_user`, locale cookie | SQL, AI calls |
| `services.py` | Domain logic: `AIService`, `ResumeService`, `JobService`, `MatchingService`, `UserService` | HTTP request handling |
| `schemas.py` | Pydantic request/response models (incl. match-details sub-models) | ORM code |
| `models.py` | 4 ORM tables: users, resumes, jobs, applications | Pydantic |
| `core/config.py` | `Settings` (pydantic-settings), `.env` loading | — |
| `core/security.py` | bcrypt hashing, PyJWT HS256 tokens, itsdangerous CSRF | HTTP |
| `core/ratelimit.py` | Login rate limiter: sliding window per IP + username, injectable clock, periodic sweep | Policy for any other endpoint |
| `core/revocation.py` | JWT `jti` denylist with expiry parity (entries dropped at the token's own `exp`) | Persistence (in-memory by design) |
| `core/i18n.py` | 20-locale translations, `normalize_locale`, `translate` (EN fallback) | — |
| `prompts/*.md` | Externalized AI prompts (`{placeholder}` substitution) | Code |

## Request flows

**Auth.** API: `OAuth2PasswordBearer` header → `get_current_user` decodes JWT
(`sub` string → int; `jti` checked against the revocation denylist), loads
user, rejects inactive. Login is rate-limited per client IP + submitted
username; logout revokes the presented token. UI: `httponly` cookie →
`get_optional_user` (anonymous-tolerant) or `get_current_user` (strict); every
authenticated form POST first validates a per-user timed CSRF token (2 h).

**Resume ingestion.** Upload → extension allow-list → streaming size cap →
extract text (Gemini PDF vision → pypdf local fallback; python-docx; raw text)
→ `AIService.parse_resume` (LLM JSON → heuristic extraction) → ORM row.

**Matching.** `match_resume_to_job` = `calculate_match_score` (LLM JSON →
heuristic set-intersection score) + `generate_resume_feedback` (LLM → heuristic
strengths/improvements). Score caching is not implemented; each apply/recompute
re-runs the scorer.

**Skills gap.** Deterministic set operations produce gap score + missing skills
with importance + learning path; an LLM pass may rewrite/enrich the result if a
provider is available.

## AI provider strategy

`AIService.call_text` tries `AI_PRIMARY_PROVIDER` then `AI_FALLBACK_PROVIDER`;
both degrade to `None` when unconfigured; callers fall back to deterministic
heuristics. Google calls are async-native; OpenRouter (OpenAI SDK) runs in
`asyncio.to_thread`. `parse_json` extracts the first balanced JSON object from
LLM prose.

## Data model

users 1—n resumes 1—n applications n—1 jobs n—1 users(recruiter).
JSON columns for skills/experience/education/projects/certifications/
achievements/required_skills/preferred_skills/responsibilities/qualifications/
priority_weights/match_details/feedback — schema-flexible but unindexed;
designed for SQLite-first single-node deployment.

## Concurrency & lifecycle

One `AsyncSession` per request via `get_db`; services commit + refresh.
Schema policy (ADR-0001): Alembic (`migrations/`, wired to
`Base.metadata` + the settings URL) is the canonical path for schema
changes — `uv run alembic upgrade head` against an existing database, or a
fresh one. The lifespan still calls `create_all`, which is a no-op on an
up-to-date schema and keeps zero-config first runs working; it is never a
substitute for a revision. CI runs an `alembic upgrade head` smoke step on
a fresh database.

## Known architectural debts

See `docs/AUDIT.md`: sequential per-job AI scoring in recommendations
(A-13), String columns without lengths (A-19), coverage.py async undercount
(A-21). Fixed and closed: locale-list duplication (A-11), dead schemas
(A-12), cross-class private access (A-14), ad-hoc ORM attributes (A-15),
token-decode duplication (A-16), no migrations (A-28 — Alembic adopted,
2026-09-18).
