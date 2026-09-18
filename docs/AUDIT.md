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
| A-08 | Medium | api.py | Duplicate registration returns `400` instead of `409 Conflict`; auth failures return `403` instead of `401` for missing credentials (OAuth2 convention). | **Fixed** (2026-09-14, `28da562`): missing/invalid bearer credentials → 401 + `WWW-Authenticate: Bearer` via shared `_unauthenticated()` helper; duplicate registration → 409; inactive user stays 403, unknown user 404. Regression tests for all four boundaries. |
| A-09 | Medium | ui.py | Hardcoded English error strings (`"Invalid email or password"`, `"Email already registered"`, …) bypass the `t()` i18n pipeline required by agents.md. | **Fixed** (2026-09-14, `00bb731`): all 7 UI error strings (login, register ×2, resume create ×2, job create, job edit) routed through `t()`; keys added to EN + real translations in all 19 locale overrides; tests pin per-locale overrides and localized rendering. |
| A-10 | Medium | api.py/schemas.py | `UserCreate.password` has no minimum-length policy (1-char passwords accepted). | **Fixed** (2026-09-14, `bcb6fc6`): min 8 (`MIN_PASSWORD_LENGTH` in schemas.py) enforced by `UserCreate` validator (422) and by the UI `/register` form (400 + rendered error), closing both registration paths. Boundary tests at schema/API/UI levels. See A-25 for why the constant lives in schemas.py. |
| A-11 | Medium | core | `SUPPORTED_LOCALES` duplicated in `core/config.py` and `core/i18n.py` — two sources of truth can drift. | **Fixed** (2026-09-14, `d2f944d`): `Settings.DEFAULT_LOCALE` derives from `BASE_LOCALE` and `SUPPORTED_LOCALES` from a defensive copy of the i18n list (env override still possible); derivation + copy-isolation pinned by test. |
| A-12 | Medium | schemas.py | Unused/dead schemas: `UserUpdate`, `ResumeCreate`, `ResumeUpdate`, `ApplicationUpdate`, `SkillBase`, `ExperienceBase`, `EducationBase`, `ProjectBase`, `CertificationBase`, `AchievementBase` are never imported anywhere. | **Deleted** (2026-09-14, `4c02452`): all ten removed after verifying zero references (ResumeBase composes `dict` sections, not these models); the one test constructing `ResumeCreate` now covers `ResumeUpload`. |
| A-13 | Medium | services.py | `JobService.get_recommendations` scores up to 100 jobs sequentially, each an AI round-trip (or heuristic) — slow path on recruiter-scale job lists. | Open — re-confirmed 2026-09-14: any fix (batching, persisted scores, concurrency) changes cost/latency behaviour and needs product input before implementation. |
| A-14 | Medium | services.py | `analyze_skills_gap` reaches into `self.ai._extract_skill_names` / `ai._call_text` (private members across classes). | **Fixed** (2026-09-14, `5bf6d78`): skill-name extraction promoted to module-level `extract_skill_names()`; provider fallback chain renamed to public `AIService.call_text()`; no cross-class private access remains (grep-verified). Tests use the public module function. |
| A-15 | Medium | ui.py | Applications list attaches ad-hoc attributes (`app.job_title`, `app.resume_name`) to ORM instances and loops per-id fetches; works but brittle and N+1-ish. | **Fixed** (2026-09-14, `33172b0` + `5157282`): template receives plain dict rows; jobs/resumes fetched in two batch queries via new `JobService.get_jobs_by_ids`/`ResumeService.get_resumes_by_ids`; new `contact_section()` helper reads contact info from the stored payload's nested shape — fixing latent "Unnamed Resume"/missing-contact rendering (list, detail, skills-gap selector and `/applications/create` defaults). Full UI-flow regression tests. |
| A-16 | Low | api.py | Bearer-prefix stripping via `token.replace("Bearer ", "", 1)` applied to cookie tokens too; harmless but sloppy. Also token decode logic duplicated between api.py and ui.py. | **Fixed** (2026-09-14, `b4d5d29`): single `core/security.decode_token_subject()` (Bearer-strip + decode + sub extraction); api/ui drop their duplicated decode blocks and the UI broad `except`; API 401/403/404 semantics unchanged. Six decode tests added. |
| A-17 | Low | services.py | `delete_resume` does sync `os.remove` inside async path; file-DB consistency not transactional. | **Fixed** (2026-09-14, `4182954`): `aiofiles.os.remove` off the event loop, `FileNotFoundError` suppressed so a vanished upload cannot block the DB delete; test covers the missing-file path. |
| A-18 | Low | main.py | `os.makedirs("static")` / `StaticFiles(directory="static")` depend on process CWD. | **Fixed** (2026-09-14, `486423f`): `STATIC_DIR` resolved from `main.py`'s location; `UPLOAD_DIR` bootstrap now uses `parents=True` while staying settings-driven. Test pins absolute resolution. |
| A-19 | Low | models.py | `String` columns have no lengths; fine on SQLite/PG but worth normalizing. | Open |
| A-20 | Low | docs | README/agents.md stale: "113 tests" (actual 124 at audit time); agents.md still says "python-jose JWT" after the PyJWT migration (`abf9c8b`). | **Fixed** in docs refresh |
| A-21 | Info | tooling | Coverage undercount bug (documented in EVALUATION.md): on FastAPI + aiosqlite + coverage 7.13.4, code resumed after an `await db.execute(...)` suspension is not recorded — reproducible with a 14-line Starlette repro, on Python 3.12.14 and 3.13.15, under both `sysmon` and `ctrace` cores. Measured coverage of `api.py`/`services.py`/`ui.py` therefore undercounts truly-executed lines. | Documented; coverage gate scoped accordingly |
| A-22 | Info | security.py | bcrypt direct (no passlib) — correct 72-byte handling relies on bcrypt 4+/5 behavior; PyJWT HS256 with `settings.SECRET_KEY`; CSRF via itsdangerous timed serializer (2 h max age). No issues found. | None |
| A-23 | Info | i18n.py | `normalize_locale`/`translate` fallback chain is correct; all 20 locales carry full EN key sets (tested). | None |
| A-24 | Medium | ui.py | `edit_job_submit` read parsed skills from the wrong dict level (`result.get("required_skills")` instead of `result["parsed_data"]`), wiping extracted skills on every UI job edit. | **Fixed** + regression test |
| A-25 | Medium | tooling/schemas | Discovered 2026-09-14 during A-10 remediation: once `schemas.py` imported `core.security` (bcrypt), pytest-cov's early import of `--cov` target modules loaded bcrypt under one `sys.path` identity and the test-time import re-imported `core` under another — PyO3 aborts with "PyO3 modules compiled for CPython 3.8 or older may only be initialized once per interpreter process", killing the documented multi-target coverage command. `tests/conftest.py`'s runtime `sys.path.insert` was the second identity. | **Fixed** (2026-09-14, `3666f9c`): `MIN_PASSWORD_LENGTH` moved into schemas.py (imports stay light; enforced there anyway), conftest hack replaced by `pythonpath = ["."]` ini. Verified: documented 4-flag command green; module-name flags (`--cov=api --cov=services --cov=ui`) work; residual: file-style `--cov=api.py` still aborts because api.py itself imports `core.security` — pre-existing since the bcrypt/JWT era, avoid file-style flags for api/ui or keep them out of docs. **Follow-up (2026-09-18)**: file-style flags proved worse than noisy — under coverage 7.16.x, `--cov=models.py`/`--cov=schemas.py` emitted "Module models.py was never imported" and **silently dropped those targets from measurement**, narrowing the CI gate to core+db (211 stmts) while still reporting 100%. CI now uses module-name flags and the gate measures the documented 469 statements. |
| A-26 | Infra | api.py | No rate limiting on the login endpoint — unbounded credential stuffing/brute force (EVALUATION limitation 5). | **Fixed** (2026-09-14, `9abb453`): per-IP + submitted-username sliding-window limiter on `POST /api/v1/auth/login` (`core/ratelimit.py`; 5 attempts / 300 s via `LOGIN_RATE_LIMIT_*` settings), 429 + `Retry-After` on excess; blocked attempts are not recorded so lockouts cannot be extended. In-memory by design: per worker under multi-worker deployments, reset on restart — Redis-style shared store is the upgrade path. Registration remains unlimited (separate decision). |
| A-27 | Infra | core/security.py | JWTs were stateless with no revocation beyond the 5-day expiry (EVALUATION limitation 6). | **Fixed** (2026-09-14, `d4b4b40`): tokens carry a `jti`; `core/revocation.py` denylist with expiry parity (entries dropped at the token's own `exp`); shared `decode_token_subject` enforces it on both API and UI; `POST /api/v1/auth/logout` and the UI logout revoke the presented token. Restart clears the denylist (pre-restart revocations lapse until token expiry) and limits are per worker — documented; shared store is the upgrade path. Legacy jti-less tokens validate but cannot be revoked. |
| A-28 | Infra | repo | No DB migration tool — `create_all` only; column changes need manual steps (EVALUATION limitation 1). | **Fixed** (2026-09-18, docs/adr/0001): Alembic adopted — `migrations/env.py` wired to settings + `Base.metadata` (async recipe, secrets stay out of alembic.ini); baseline revision autogenerated from the models and reviewed op by op; verified: fresh DB upgrade head matches `create_all` (10/10 schema objects after normalizing the `DEFAULT (CURRENT_TIMESTAMP)` text rendering), downgrade base → re-upgrade round-trips; CI `alembic upgrade head` smoke step added. Startup policy: `create_all` kept for fresh DBs, revision chain is the change path (ARCHITECTURE.md "Concurrency & lifecycle"). |
| A-29 | Infra | repo/uv.lock | Dependabot alerts: triage brief of 2026-09-16 listed 64 open; live API shows 66 total, **0 open** — the snapshot was stale and Dependabot's re-scan after the Sep-2026 lock refresh (`3055cb2`) auto-resolved all of them. Manually verified every locked version ≥ `first_patched_version` (cryptography 50.0.1, starlette 1.6.0, pypdf 6.18.0, python-multipart 0.0.32, pyjwt 2.13.0, urllib3 2.7.0, plus pyasn1/idna/lxml/requests/pydantic-settings/python-dotenv/pygments/pytest); both `ecdsa` alerts (GHSA-wj6h-64fc-37mp) closed because the dependency left the graph entirely. | **Closed — no action** (2026-09-16): no bump warranted; every locked version already current. Residual observation: `pyproject.toml` floor `pypdf>=6.1.0` predates the patched minors (committed lock is authoritative at 6.18.0, so no vulnerable resolution path) — **tightened (2026-09-16 follow-up pass)**: floor raised to `pypdf>=6.18.0` (pyproject.toml + lock `requires-dist` line only; locked version unchanged at 6.18.0, `uv lock --check` clean), so a fresh resolve can no longer pick a vulnerable pypdf. |

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

## Post-remediation coverage (pytest-cov, Windows, Py 3.12.14, 2026-09-14)

After the A-08..A-18/A-25 remediation pass (180 tests). "undercounted" = A-21 applies.
Measured with module-name flags (`--cov=core --cov=db --cov=models --cov=schemas
--cov=api --cov=services --cov=ui --cov=main`); see A-25 for the file-style flag quirk.

| Module | Stmts | Miss | Cover |
|---|---|---|---|
| core/config.py | 43 | 0 | 100% |
| core/i18n.py | 16 | 0 | 100% |
| core/security.py | 49 | 0 | 100% |
| db/database.py | 12 | 0 | 100% |
| models.py | 77 | 0 | 100% |
| schemas.py | 181 | 0 | 100% (10 dead schemas removed, A-12) |
| main.py | 32 | 8 | 75% |
| services.py | 510 | 195 | 62% (undercounted) |
| api.py | 240 | 118 | 51% (undercounted) |
| ui.py | 356 | 211 | 41% (undercounted + real gaps) |

Gated set (core/, db/, models.py, schemas.py) remains 100% — CI gate ≥95% satisfied.
