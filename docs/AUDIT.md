# Codebase Audit — Samarth AI

Audited 2026-09-08/09 (UTC+5:30) at commit `ec017a9` (main). Scope: every Python module,
templates structure, tests, CI, Docker, docs. Baseline: 124 tests pass; ruff clean.

## Findings index

| ID | Severity | Area | Finding | Action |
|---|---|---|---|---|
| A-01 | High | services.py | `MAX_UPLOAD_SIZE` (10 MB) is defined in settings but never enforced — `process_resume_file` streams files of unbounded size to disk (DoS vector). | **Fixed**: streaming size cap enforced; 413 on violation |
| A-02 | High | services.py | No upload extension whitelist — any file type (`.exe`, `.html`, …) is accepted and stored; unknown types silently read back as UTF-8 text. | **Fixed**: allow-list `.pdf`/`.docx`/`.txt` (README contract); 415 otherwise |
| A-03 | High | ui.py | Open redirect: `POST /set-locale` accepts arbitrary `redirect_to` (e.g. `https://evil.com`) and redirects there. | **Fixed**: only same-origin relative paths allowed |
| A-04 | High | ui.py | `get_optional_user` passes JWT `sub` (str) straight to `db.get(UserModel, …)`; relies on DB coercion (breaks on PostgreSQL int PK strictness). api.py does the int conversion correctly. | **Fixed**: parse to int, reject malformed tokens |
| A-05 | High | ui.py | Exception messages leaked into HTML: `create_resume_submit` / `create_job_submit` / `edit_job_submit` render `str(e)` (may include file paths, DB details) to the user. | **Fixed**: generic user-facing error; detail goes to server log |
| A-06 | High | repo | `.gitignore` pattern `.env.*` silently ignores `.env.example`. It was committed in `88d9b82` per the log but is absent from the working tree/README instructions fail. | **Fixed**: `!.env.example` un-ignore + file added |
| A-07 | Medium | ci.yml | `ty check` runs with `continue-on-error: true` — type checking is advisory only; tests run without a coverage gate. | **Fixed**: type check is blocking; coverage gate added (see EVALUATION.md for threshold rationale) |
| A-08 | Medium | api.py | Duplicate registration returns `400` instead of `409 Conflict`; auth failures return `403` instead of `401` for missing credentials (OAuth2 convention). | Open (behavior change; API consumers may depend on current codes) |
| A-09 | Medium | ui.py | Hardcoded English error strings (`"Invalid email or password"`, `"Email already registered"`, …) bypass the `t()` i18n pipeline required by agents.md. | Open (needs 20-locale translations; tracked as i18n debt) |
| A-10 | Medium | api.py/schemas.py | `UserCreate.password` has no minimum-length policy (1-char passwords accepted). | Open (product decision; recommend min 8 via schema validator) |
| A-11 | Medium | core | `SUPPORTED_LOCALES` duplicated in `core/config.py` and `core/i18n.py` — two sources of truth can drift. | Open (low-risk dedup; i18n is the domain owner) |
| A-12 | Medium | schemas.py | Unused/dead schemas: `UserUpdate`, `ResumeCreate`, `ResumeUpdate`, `ApplicationUpdate`, `SkillBase`, `ExperienceBase`, `EducationBase`, `ProjectBase`, `CertificationBase`, `AchievementBase` are never imported anywhere. | Open (candidate for deletion in a breaking-changes pass) |
| A-13 | Medium | services.py | `JobService.get_recommendations` scores up to 100 jobs sequentially, each an AI round-trip (or heuristic) — slow path on recruiter-scale job lists. | Open (batch/persist scores; needs product input) |
| A-14 | Medium | services.py | `analyze_skills_gap` reaches into `self.ai._extract_skill_names` / `ai._call_text` (private members across classes). | Open (promote helpers to module functions) |
| A-15 | Medium | ui.py | Applications list attaches ad-hoc attributes (`app.job_title`, `app.resume_name`) to ORM instances and loops per-id fetches; works but brittle and N+1-ish. | Open (use a dict/DTO in template context) |
| A-16 | Low | api.py | Bearer-prefix stripping via `token.replace("Bearer ", "", 1)` applied to cookie tokens too; harmless but sloppy. Also token decode logic duplicated between api.py and ui.py. | Open |
| A-17 | Low | services.py | `delete_resume` does sync `os.remove` inside async path; file-DB consistency not transactional. | Open |
| A-18 | Low | main.py | `os.makedirs("static")` / `StaticFiles(directory="static")` depend on process CWD. | Open |
| A-19 | Low | models.py | `String` columns have no lengths; fine on SQLite/PG but worth normalizing. | Open |
| A-20 | Low | docs | README/agents.md stale: "113 tests" (actual 124 at audit time); agents.md still says "python-jose JWT" after the PyJWT migration (`abf9c8b`). | **Fixed** in docs refresh |
| A-21 | Info | tooling | Coverage undercount bug (documented in EVALUATION.md): on FastAPI + aiosqlite + coverage 7.13.4, code resumed after an `await db.execute(...)` suspension is not recorded — reproducible with a 14-line Starlette repro, on Python 3.12.14 and 3.13.15, under both `sysmon` and `ctrace` cores. Measured coverage of `api.py`/`services.py`/`ui.py` therefore undercounts truly-executed lines. | Documented; coverage gate scoped accordingly |
| A-22 | Info | security.py | bcrypt direct (no passlib) — correct 72-byte handling relies on bcrypt 4+/5 behavior; PyJWT HS256 with `settings.SECRET_KEY`; CSRF via itsdangerous timed serializer (2 h max age). No issues found. | None |
| A-23 | Info | i18n.py | `normalize_locale`/`translate` fallback chain is correct; all 20 locales carry full EN key sets (tested). | None |
| A-24 | Medium | ui.py | `edit_job_submit` read parsed skills from the wrong dict level (`result.get("required_skills")` instead of `result["parsed_data"]`), wiping extracted skills on every UI job edit. | **Fixed** + regression test |

## Verified-good (no action)

- Auth: bcrypt hashing per-user salt; JWT `sub` always stringified; cookie flags from settings; CSRF token bound to user id and time-limited; CSRF enforced on all authenticated UI form POSTs.
- Ownership checks on resume/job/application reads, updates, deletes (API + UI).
- aiJSON extraction (`parse_json`) is hand-rolled but bracket-tracking and tested; heuristic fallbacks keep flows alive without API keys.
- Docker: non-root user, named volumes, healthcheck, resource limits.
- No secrets in code; `.env` only in settings; CORS from settings.

## Coverage baseline at audit time (pytest-cov, Windows, Py 3.12.14)

Post-fix numbers (153 tests); "undercounted" = A-21 applies.

| Module | Stmts | Miss | Cover |
|---|---|---|---|
| core/security.py | 39 | 0 | 100% |
| core/i18n.py | 16 | 0 | 100% |
| core/config.py | 41 | 0 | 100% (was 98%) |
| db/database.py | 12 | 0 | 100% (was 83%) |
| models.py | 77 | 0 | 100% |
| schemas.py | 220 | 0 | 100% |
| main.py | 31 | 8 | 74% |
| services.py | 487 | 197 | 60% (undercounted) |
| api.py | 246 | 123 | 50% (undercounted) |
| ui.py | 368 | 244 | 34% (undercounted + real gaps) |

Full analysis: docs/EVALUATION.md.
