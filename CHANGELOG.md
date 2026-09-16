# Changelog

All notable changes to Samarth AI are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); versioning is
[SemVer](https://semver.org/)-flavoured.

## [Unreleased]

### Security

- Dependabot alert triage (docs/AUDIT.md A-29): 66 alerts on record, **0
  open** — the earlier "64 open" snapshot was stale; Dependabot's re-scan
  after the v0.6.0 `uv.lock` refresh auto-resolved all of them, and each
  locked version was manually verified at or above the advisories'
  `first_patched_version`. No dependency bumps required.
- Follow-up: `pypdf` floor raised from `>=6.1.0` to `>=6.18.0` in
  `pyproject.toml` (locked version unchanged at 6.18.0), so a fresh resolve
  can no longer pick a vulnerable pypdf.

### Docs

- STATUS.md / AUDIT.md record the triage evidence (locked-version table,
  `ecdsa` graph-removal note, pypdf floor tightening).

## [0.6.0] - 2026-09-14

Infra-hardening pass (docs/AUDIT.md A-26, A-27): login brute-force
protection and a JWT revocation story.

### Added

- **Login rate limiting**: `POST /api/v1/auth/login` is limited per client IP
  + submitted username with an in-memory sliding window (5 attempts / 300 s by
  default, `LOGIN_RATE_LIMIT_ATTEMPTS` / `LOGIN_RATE_LIMIT_WINDOW_SECONDS`).
  Exceeding it returns **429 Too Many Requests** with a `Retry-After` header.
  Single-process by design: limits are per worker under multi-worker
  deployments and reset on restart (A-26).
- **JWT revocation**: access tokens carry a `jti` claim; a new
  `POST /api/v1/auth/logout` endpoint (and the UI logout) revokes the
  presented token for the rest of its lifetime via an in-memory denylist with
  expiry parity. Revoked tokens fail authentication on both the API and the
  UI. Restart clears the denylist, so pre-restart revocations lapse until the
  token's own expiry (A-27).

## [0.5.0] - 2026-09-14

Audit-remediation pass (docs/AUDIT.md A-08..A-18, A-25). Breaking API
behaviour changes are listed first.

### Changed (breaking for API consumers)

- Auth failures for missing/invalid bearer credentials now return
  **401 Unauthorized** with a `WWW-Authenticate: Bearer` challenge instead of
  403 (audit A-08). 403 remains reserved for authenticated-but-forbidden
  requests (inactive user, non-owner, wrong role).
- Duplicate registration now returns **409 Conflict** instead of 400 (A-08).
- Registration now enforces a **minimum password length of 8** on both the API
  (`422` from the `UserCreate` validator) and the UI form (`400` with a
  rendered error) (A-10).

### Fixed

- UI error messages (login, registration, resume/job processing) are routed
  through the i18n pipeline and translated in all 20 locales instead of being
  hardcoded English (A-09).
- Applications list renders plain dict rows from two batch queries instead of
  mutating ORM instances with per-id fetch loops (A-15).
- Resume lists, resume details and the skills-gap selector now actually render
  parsed contact info; previously the nested payload shape made every read
  miss and fall back to "Unnamed Resume" (A-15 follow-up).
- Resume deletion removes files off the event loop (`aiofiles`) and tolerates
  an already-vanished file (A-17).
- Static assets resolve from the repository root instead of the process CWD
  (A-18).

### Removed

- Ten unused schemas (`UserUpdate`, `ResumeCreate`, `ResumeUpdate`,
  `ApplicationUpdate`, `SkillBase`, `ExperienceBase`, `EducationBase`,
  `ProjectBase`, `CertificationBase`, `AchievementBase`) — dead code (A-12).

### Refactored

- `SUPPORTED_LOCALES`/`DEFAULT_LOCALE` derive from `core/i18n.py`, the domain
  owner, removing a drift-prone duplicate (A-11).
- No cross-class private access in services: `extract_skill_names()` is a
  module function and the provider fallback chain is public
  `AIService.call_text()` (A-14).
- Single shared `core/security.decode_token_subject()` replaces the duplicated
  JWT decode blocks in api.py/ui.py (A-16).

### Tooling

- Restored multi-target pytest-cov runs: password policy constant kept inside
  schemas.py (import-light) and conftest's runtime `sys.path` hack replaced by
  pytest `pythonpath` ini (A-25).

## [0.4.0] - 2026-09-09

Initial audited release: FastAPI + Jinja SSR platform, AI provider routing
with heuristic fallbacks, 20-locale i18n, upload hardening, CSRF, JWT auth,
CI with blocking type check and coverage gate. See docs/AUDIT.md (A-01..A-24)
and docs/EVALUATION.md.
