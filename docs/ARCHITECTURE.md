# Architecture — Samarth AI

## System overview

```
Browser ──► main.py (FastAPI app)
             ├── /api/v1/*  → api.py    (REST, Bearer JWT)
             ├── /*         → ui.py     (Jinja2 SSR, session cookie + CSRF)
             ├── /static    → StaticFiles
             └── lifespan: create_all on startup
                        │
                        ▼
                  services.py ──── AIService (Google GenAI → OpenRouter → heuristics)
                        │
                        ▼
                  models.py (SQLAlchemy 2.0 async ORM)
                        │
                        ▼
              db/database.py → aiosqlite (SQLite) / asyncpg (PostgreSQL)
```

## Modules

| Module | Responsibility | Must not contain |
|---|---|---|
| `main.py` | App factory wiring, CORS, static mount, lifespan (DDL create_all) | Business logic |
| `api.py` | REST routes `/api/v1/*`, `get_current_user` (JWT → user), permission checks | SQL, AI calls |
| `ui.py` | SSR routes, form handling, CSRF validation, `get_optional_user`, locale cookie | SQL, AI calls |
| `services.py` | Domain logic: `AIService`, `ResumeService`, `JobService`, `MatchingService`, `UserService` | HTTP request handling |
| `schemas.py` | Pydantic request/response models (incl. match-details sub-models) | ORM code |
| `models.py` | 4 ORM tables: users, resumes, jobs, applications | Pydantic |
| `core/config.py` | `Settings` (pydantic-settings), `.env` loading | — |
| `core/security.py` | bcrypt hashing, PyJWT HS256 tokens, itsdangerous CSRF | HTTP |
| `core/i18n.py` | 20-locale translations, `normalize_locale`, `translate` (EN fallback) | — |
| `prompts/*.md` | Externalized AI prompts (`{placeholder}` substitution) | Code |

## Request flows

**Auth.** API: `OAuth2PasswordBearer` header → `get_current_user` decodes JWT
(`sub` string → int), loads user, rejects inactive. UI: `httponly` cookie →
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

`AIService._call_text` tries `AI_PRIMARY_PROVIDER` then `AI_FALLBACK_PROVIDER`;
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
Schema changes are applied via `create_all` at startup — **no migration
tool** (Alembic is future work); destructive column changes need manual steps.

## Known architectural debts

See `docs/AUDIT.md`: duplicated locale list (A-11), dead schemas (A-12),
sequential per-job AI scoring in recommendations (A-13), cross-class private
access in skills-gap (A-14), ad-hoc ORM attributes in UI applications list (A-15),
token-decode duplication between api.py/ui.py (A-16), no migrations.
