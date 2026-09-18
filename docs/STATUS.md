# Status — honest state

Updated: 2026-09-18 (IST): production-completion pass in progress. The last
recorded residual (A-28, Alembic) is being executed per the six-step plan
below; decisions in docs/adr/0001. Baseline at pass start (as-found,
Windows/Py 3.12.14, `uv sync --all-groups` fresh): ruff format 46 files
clean, ruff check 0 diagnostics, ty 0 diagnostics, pytest **206 passed,
2 warnings** (the two pre-existing `InsecureKeyLengthWarning` fixture
warnings in `tests/test_security.py`), gated coverage 100% (core 199 stmts,
db 12, models 77, schemas 181), full matrix TOTAL 67% with the known A-21
async undercount (api 53%, services 62%, ui 42%, main 75%). This section is
re-measured and finalized at the end of the pass; intermediate states are
not recorded here.

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

- **A-28 (Infra) — Alembic migrations: NOT started, deferred deliberately.**
  A half-configured Alembic is worse than none, and the window did not allow
  init + baseline + a *verified* upgrade. Exact remaining steps for the next
  session:
  1. `uv add alembic` (dev/main group per repo convention), then
     `uv run alembic init migrations`.
  2. Wire `migrations/env.py` to `models.Base.metadata` and
     `settings.DATABASE_URL` using the async recipe (`async_engine_from_config`
     + `connection.run_sync`), keeping secrets out of the file.
  3. Create the baseline against an empty DB with
     `uv run alembic revision --autogenerate -m "baseline schema"` (models are
     the source of truth), then review the generated ops line by line.
  4. Verify: fresh empty DB → `uv run alembic upgrade head` → schema matches
     what `Base.metadata.create_all` produces (diff `sqlite_master` dumps);
     also verify `alembic downgrade base` round-trips.
  5. Decide and document the startup policy in docs/ARCHITECTURE.md
     ("Concurrency & lifecycle"): keep `create_all` as dev convenience with
     `alembic upgrade head` as the real path, or drop `create_all`.
  6. CI: add an `alembic upgrade head` smoke step.
- **Registration is not rate-limited** (A-26 scope was login only); no
  account lockout anywhere. Multi-worker/Redis upgrade paths for the limiter
  and denylist are documented, not built (A-26/A-27).
- **Medium**: sequential AI scoring in recommendations (A-13 — needs product
  input before batching/persistence decisions).
- **Low**: models.py `String` column lengths (A-19).
- **Info**: coverage.py undercount upstream (A-21; a coverage.py issue would
  be the right home).
- Residual tooling quirk: file-style `--cov=api.py` / `--cov=ui.py` flags
  abort on this Windows venv (A-25); use module-name flags (`--cov=api`).

## Verification commands

```bash
uv sync --all-groups
uv run ruff format --check . && uv run ruff check . && uv run ty check
uv run pytest tests/ -v --cov=core --cov=db --cov=models.py --cov=schemas.py --cov-fail-under=95
# full table incl. reported-only modules (module-name flags; see AUDIT A-25):
uv run pytest tests/ -q --cov=core --cov=db --cov=models --cov=schemas --cov=api --cov=services --cov=ui --cov=main
```

All gates were run and green immediately before this file was committed
(206/206 tests; gated coverage 100% incl. the two new core modules).

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
