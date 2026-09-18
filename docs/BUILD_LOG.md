# Build log

The engineering history of the project: what was built, what was tested,
what was rejected, and why the chosen approach won. Newest last. Point-in-time
findings live in AUDIT.md; the current measured state lives in STATUS.md.

## Phase 1 — initial build (2026-09-08 and before)

The first version shipped the whole product surface: FastAPI app with a REST
API and a Jinja2 SSR UI over one service layer, SQLAlchemy 2.0 async against
SQLite, the Google GenAI → OpenRouter → heuristic provider chain, bcrypt/JWT
auth with CSRF on form writes, 20-locale i18n, Docker packaging, and 124
tests. Two decisions from this phase still shape everything:

- **Heuristic fallbacks for every AI flow.** Tested by disabling provider
  clients in tests, which forced the design to make "no keys" a first-class
  operating mode rather than an error path.
- **`create_all` at startup** for schema setup. Convenient, and it became
  A-28 much later.

## Phase 2 — full audit (2026-09-08/09)

A line-by-line audit at commit `ec017a9` produced findings A-01..A-24
(docs/AUDIT.md). The serious ones: unbounded upload size (A-01), no upload
type allow-list (A-02), an open redirect in `/set-locale` (A-03), a JWT `sub`
handed to the DB without int parsing, which would break on PostgreSQL
(A-04), and exception text rendered into HTML (A-05). Also recorded: `ty`
type check ran with `continue-on-error` in CI, making it advisory (A-07).

## Phase 3 — audit remediation, v0.5.0 (2026-09-14, 11 commits)

All Medium/Low findings fixed at the root, one commit per finding with
regression tests. Choices worth remembering:

- **Auth error semantics** moved to 401 + `WWW-Authenticate` for missing
  credentials and 409 for duplicate registration. The tempting shortcut was
  to keep 400/403 everywhere and document it; the OAuth2 convention won
  because API clients already speak it.
- **Token decoding** was duplicated in api.py and ui.py with a broad except
  in the UI. Both now call one `core/security.decode_token_subject()`. When
  revocation arrived later, this single choke point is what made API and UI
  die together.
- **Ten dead Pydantic schemas deleted** (A-12) after grep-verifying zero
  references. Kept: `ResumeBase`, which composes `dict` sections.
- **Applications list** rebuilt from plain dict rows with two batch queries
  (A-15), replacing ad-hoc attributes attached to ORM instances. This also
  fixed a latent bug where parsed contact info rendered as "Unnamed".
- **A tooling landmine (A-25).** Adding bcrypt to schemas.py made pytest-cov
  import the module twice under different `sys.path` identities, and the
  PyO3 bcrypt core aborted the process. Root cause: conftest's runtime
  `sys.path.insert` plus pytest-cov's early import. Fix: `pythonpath = ["."]`
  in pytest.ini and keeping schemas.py import-light (the password-length
  constant moved into schemas.py for this reason). Residual: file-style
  `--cov=api.py` flags still abort on this venv; module-name flags are the
  documented form.
- **Coverage undercount investigation (A-21).** Numbers for api.py /
  services.py / ui.py looked impossibly low. Root-caused with a 14-line
  Starlette repro: code resumed after an await on the aiosqlite worker
  thread is not recorded by coverage.py, on 3.12 and 3.13, under sysmon and
  ctrace, and unfixed in coverage 7.13.4 → 7.16.0. Rather than distrust all
  numbers, the CI gate is scoped to the fully-measurable modules (core/, db/,
  models, schemas; 100%) and the rest are reported as deterministic lower
  bounds. Rejected: deleting the coverage gate, or silently shipping
  misleading percentages.

## Phase 4 — infra hardening, v0.6.0 (2026-09-14)

Two infrastructure gaps became features:

- **Login rate limiting (A-26).** Sliding window per client IP + submitted
  username, 429 + `Retry-After`, injectable clock for tests, periodic sweep
  to bound memory. Deliberate scope cuts, each recorded: registration stays
  unlimited (separate threat model, needs its own decision), and the store is
  in-memory, so limits are per worker and reset on restart. A Redis store is
  the upgrade path; it was not built because this deployment is single-node
  and the caveat is documented everywhere a user would look.
- **JWT revocation (A-27).** Tokens carry a `jti`; logout (API and UI)
  pushes it to a denylist that drops entries at the token's own expiry.
  Same honest limits: per worker, cleared on restart, and legacy tokens
  without a `jti` validate but cannot be revoked.

## Phase 5 — dependency and supply-chain pass (2026-09-16)

The whole dependency set was upgraded to September-2026 stable via
`uv lock --upgrade` (v0.6.0 lock refresh). GitHub's Dependabot later showed
"64 open" alerts; the live API showed all 66 historical alerts already in
`fixed` state after the lock refresh. Every locked version was checked
against the advisory `first_patched_version` by hand. Residual tightened:
the `pypdf>=6.1.0` floor predated several patched minors, so it was raised to
`>=6.18.0` to keep fresh resolves safe even though the committed lock was
already current. Lesson: a lockfile is a snapshot; the constraint floor is
what a fresh clone resolves against.

## Phase 6 — migrations and production completion (2026-09-18)

The last recorded residual (A-28) got its six-step plan executed:

- Alembic adopted per ADR-0001: `migrations/env.py` wired to
  `Base.metadata` + settings URL (async recipe), baseline revision
  autogenerated from the models and reviewed op by op, verified against an
  empty database (upgrade → schema matches `create_all`; downgrade
  round-trips).
- **Startup decision:** `create_all` stays as dev convenience, Alembic is
  the real change path. Alternatives (drop create_all; upgrade-on-startup
  in the lifespan) evaluated and rejected in the ADR.
- CI gained an `alembic upgrade head` smoke step against a fresh database.
- Full dependency refresh re-run (`uv lock --upgrade`), dead-code analysis
  (vulture + deptry) run and findings resolved, gates re-measured from a
  clean state, and the doc set (README, design.md, this log, CONTRIBUTING)
  rebuilt around the real, executed commands.

Measured results for this phase are recorded with dates in STATUS.md and
EVALUATION.md.
