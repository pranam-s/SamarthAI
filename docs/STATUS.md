# Status — honest state

Updated: 2026-09-18 (IST): production-completion pass COMPLETE at v0.7.0
(HEAD `cbf59b4` at gate time). A-28 (Alembic) executed per the recorded
six-step plan, decision in docs/adr/0001. All gates re-run from a clean
tree (nothing uncommitted) immediately before this update.

## Final gate, 2026-09-18 (clean tree, real output)

| Gate | Result |
|---|---|
| `ruff format --check .` | clean (47 files) |
| `ruff check .` | 0 diagnostics |
| `ty check` | 0 diagnostics |
| `deptry .` | no issues |
| `vulture` (src, 80% conf) | clean |
| `pytest tests/` | **206 passed, 0 warnings** in 101 s |
| Gated coverage (core+db+models+schemas) | 469/469 statements, **100%** |
| Full coverage matrix | TOTAL 67% — api 53%, services 62%, ui 42%, main 75% (deterministic lower bounds, A-21) |
| `alembic upgrade head` (fresh DB) | upgrade → downgrade base → upgrade all clean |
| CI jobs (quality + test incl. coverage gate ≥95% + migration smoke) | every command executed locally, all green; Actions stay disabled on GitHub per the owner's zero-spend policy |

Dependency state: `uv lock --upgrade` re-run this pass (16 packages moved;
fastapi 0.141.1, pydantic 2.13.5, starlette 1.6.0, pytest 9.1.1 were
already latest). License audit of all 67 installed distributions: MIT /
BSD / Apache-2.0 / PSF plus certifi (MPL-2.0, file-level copyleft,
data-only — no conflict with the repo MIT license); LICENSE MIT text
verified intact (warranty disclaimer and liability clauses present).

Feature run (2026-09-18, keyless heuristic mode, real HTTP against
`uvicorn` on a migrations-built SQLite): register → login (OAuth2 form) →
me → create resume (multipart text; skills parsed) → recruiter register →
post job (skills parsed) → match (70.5 with feedback) → apply (status New,
score stored) → status update (Shortlisted) → skills-gap (score 100, no
missing skills) → recommendations (1 job) → market-analysis (skill
aggregates) → improve (4 suggestion groups) → quality-score (10.5 with
section breakdown) → base64 upload (TXT parsed) → logout → revoked token
correctly 401s → 5 bad logins then 429 + lockout. UI driven end to end in
headless Chromium with a real form login for both roles; screenshots in
docs/screenshots/ captured from that run.

Known residuals (unchanged, deliberate): A-13 sequential recommendation
scoring (needs product input); A-19 String lengths; A-21 coverage
undercount (documented, gated modules unaffected); in-memory limiter/
revocation state (single-node design, upgrade path recorded); registration
not rate-limited (separate decision). A-25 residual: never use file-style
`--cov=<file>.py` flags — coverage 7.16.x silently drops such targets
(fixed in CI this pass).

## Pass history (this pass, 2026-09-18)

- Baseline as-found (before any change): 206 passed, 2 warnings; ruff/ty
  clean; gated coverage 100%; full matrix TOTAL 67%. The two warnings were
  `InsecureKeyLengthWarning` from 26-byte wrong-key literals in
  `tests/test_security.py` — eliminated at the source this pass (keys now
  meet the RFC 7518 HS256 minimum); the suite runs warning-free.
- Commits this pass: docs baseline + design/ADR/BUILD_LOG/CONTRIBUTING →
  `chore(deps)` lock upgrade → `feat(db)` Alembic → `test` warning-free
  keys → `ci` smoke + coverage-flag fix → `refactor` dead-code tooling +
  a11y → docs/README/CHANGELOG 0.7.0.

## Previous state (2026-09-16): Dependabot alert triage complete — 0 open alerts
remain (A-29); all 66 historical alerts are in `fixed` state, verified against
`uv.lock`. v0.6.0 state (login rate limiting + JWT revocation on top of the
v0.5.0 audit-remediation pass) pushed to `origin/main` with owner
authorization; gates re-run green immediately before push.

## Dependabot triage (2026-09-16, A-29)

- GitHub reported 66 Dependabot alerts for this repo; **0 are open** — all are
  in `fixed` state. The "64 open" figure from the triage brief was a stale
  snapshot: Dependabot's re-scan after the Sep-2026 `uv.lock` refresh
  (`3055cb2`, v0.6.0) auto-resolved every alert whose locked version already
  met `first_patched_version`.
- Verified each locked version against the alerts' `first_patched_version`:
  cryptography 50.0.1 (≥ 50.0.0), starlette 1.6.0 (≥ 1.3.1), pypdf 6.18.0
  (≥ 6.16.1), python-multipart 0.0.32 (≥ 0.0.31), pyjwt 2.13.0 (= 2.13.0),
  urllib3 2.7.0 (= 2.7.0), plus pyasn1/idna/lxml/requests/pydantic-settings/
  python-dotenv/pygments/pytest — all at or above the patched floor.
- `ecdsa` alerts (GHSA-wj6h-64fc-37mp) closed with no patched release because
  the dependency is no longer in the graph at all (absent from `uv.lock` and
  `pyproject.toml`).
- No bumps applied: every locked version is already current; nothing to fix.
- Follow-up (2026-09-16, second pass): the `pypdf>=6.1.0` constraint floor
  from the observation below has been raised to `pypdf>=6.18.0` in
  `pyproject.toml` (lock `requires-dist` updated; locked version still
  6.18.0, `uv lock --check` clean, gates re-run green). A fresh resolve can
  no longer pick a vulnerable pypdf.
- Observation (superseded by the follow-up above): the `pypdf>=6.1.0`
  constraint floor in `pyproject.toml` was below several patched minors; the
  committed lock (6.18.0) was authoritative and `uv lock`/`uv sync` preserved
  it, so there was no realistic path to a vulnerable resolution.
- Gates at this commit: 206/206 tests pass (2 pre-existing short-HMAC-key
  fixture warnings, `InsecureKeyLengthWarning` in `tests/test_security.py`),
  ruff clean.

## What works right now (verified this session)

- Full quality gates green on Windows/Py 3.12.14: ruff format+lint, ty,
  206/206 tests.
- Gated coverage (core/, db/, models.py, schemas.py) 100% — including the two
  new modules `core/ratelimit.py` and `core/revocation.py` (both 100%);
  reported-only modules re-measured (services 62%, api/ui undercounted, A-21).
- Login rate limiting: `POST /api/v1/auth/login` limited per client IP +
  submitted username (sliding window, 5 attempts / 300 s,
  `LOGIN_RATE_LIMIT_*` settings), 429 + `Retry-After` on excess. Behavior
  tested at limiter level (injectable clock) and API level (429 shape,
  correct-password-still-blocked, per-username isolation).
- JWT revocation: access tokens carry `jti`; in-memory denylist with expiry
  parity (`core/revocation.py`); `POST /api/v1/auth/logout` (204) and the UI
  logout revoke the presented token; revoked tokens fail auth on both API and
  UI (shared `decode_token_subject`). Tested end to end.
- Everything from the v0.5.0 audit-remediation pass below still holds (180 of
  the 206 tests are that pass's suite).

## Changes in this pass (2 feature commits + docs commits; pushed to origin/main 2026-09-16 with owner authorization)

1. `9abb453` `feat(api)`: A-26 — login rate limiting per IP+username,
   in-memory sliding window (`core/ratelimit.py`), 429 + `Retry-After`;
   blocked attempts are not recorded (lockouts cannot be extended by
   hammering); periodic sweep bounds memory. Per-worker/reset-on-restart
   caveat documented in module docstring, README, EVALUATION, AUDIT.
2. `d4b4b40` `feat(security)`: A-27 — JWT revocation: `jti` claim +
   `core/revocation.py` denylist with expiry parity; API `POST
   /auth/logout` (401 for missing/invalid/unrevokable tokens) and UI logout
   revocation; enforced in the shared decoder so API and UI die together.
   Restart caveat documented in the same places.
3. This commit: docs sync (STATUS/AUDIT/EVALUATION/README/CHANGELOG/
   .env.example), version bump 0.5.0 → 0.6.0 (+uv.lock), and the two
   gate-restoring tests for `core/ratelimit.py` sweep/default-clock paths.

## Known open items (tracked in docs/AUDIT.md)

- **A-28 (Infra) — Alembic migrations: CLOSED 2026-09-18.** The six recorded
  steps were executed as written: alembic added to the main dependency group
  (1.20.0), `migrations/env.py` wired to `models.Base.metadata` +
  `settings.DATABASE_URL` via the async recipe with no secrets in
  alembic.ini, baseline autogenerated against an empty DB and reviewed op by
  op, verified against `create_all` (schema diff) plus a downgrade
  round-trip, startup policy documented in docs/ARCHITECTURE.md and
  docs/adr/0001, CI smoke step added and executed locally.
- **Registration is not rate-limited** (A-26 scope was login only); no
  account lockout anywhere. Multi-worker/Redis upgrade paths for the limiter
  and denylist are documented, not built (A-26/A-27).
- **Medium**: sequential AI scoring in recommendations (A-13 — needs product
  input before batching/persistence decisions).
- **Low**: models.py `String` column lengths (A-19).
- **Info**: coverage.py undercount upstream (A-21; a coverage.py issue would
  be the right home).
- Residual tooling quirk: file-style `--cov=<module>.py` flags are unsafe on
  this stack — coverage 7.16.x silently drops such targets from measurement
  (A-25 follow-up); use module-name flags (`--cov=api`, `--cov=models`).

## Verification commands

```bash
uv sync --all-groups
uv run ruff format --check . && uv run ruff check . && uv run ty check
uv run deptry . && uv run vulture main.py api.py ui.py services.py models.py schemas.py core db migrations
# CI gate (module-name flags; see AUDIT A-25 for why file-style flags are unsafe):
uv run pytest tests/ -v --cov=core --cov=db --cov=models --cov=schemas --cov-fail-under=95
# full table incl. reported-only modules:
uv run pytest tests/ --cov=core --cov=db --cov=models --cov=schemas --cov=api --cov=services --cov=ui --cov=main
uv run alembic upgrade head   # on a scratch DATABASE_URL for a throwaway check
```

All gates were run and green on the clean v0.7.0 tree immediately before
this file was committed (206/206 tests, zero warnings; gated coverage
469/469 statements, 100%; migration chain upgrade → downgrade → upgrade
verified; full table above).

---

## Previous pass (v0.5.0 audit remediation, 11 commits)

Audit remediation per docs/AUDIT.md; commit hashes are the evidence anchors:

1. `28da562` `fix(api)`: A-08 — 401 + `WWW-Authenticate` for missing/invalid
   credentials, 409 for duplicate registration; 403 reserved for
   authenticated-but-forbidden.
2. `bcb6fc6` `fix(security)`: A-10 — 8-char minimum password on both
   registration paths (API 422, UI 400), shared policy constant.
3. `d2f944d` `refactor(core)`: A-11 — locale list/default derived from
   core/i18n (single source of truth).
4. `00bb731` `fix(ui)`: A-09 — 7 hardcoded error strings routed through `t()`
   with real translations in all 19 locale overrides.
5. `4c02452` `refactor(schemas)`: A-12 — 10 dead schemas deleted.
6. `5bf6d78` `refactor(services)`: A-14 — no cross-class private access
   (`extract_skill_names()` module function, public `AIService.call_text()`).
7. `33172b0` `fix(ui)`: A-15 — applications list uses dict rows + batch
   queries; `contact_section()` fixes latent wrong-shape contact reads.
8. `5157282` `fix(ui)`: A-15 follow-up — resume list/detail/skills-gap
   templates now render parsed contact info (were silently "Unnamed").
9. `4182954` `fix(services)`: A-17 — async file removal, missing-file tolerant.
10. `486423f` `fix(main)`: A-18 — static dir resolved from repo root, not CWD.
11. `3666f9c` `fix(tests)`: A-25 — pytest-cov multi-target command restored
    (schemas import-light, conftest sys.path hack → `pythonpath` ini).
