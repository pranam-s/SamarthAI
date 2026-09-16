# Evaluation & Limitations

All numbers below were measured on 2026-09-16 (UTC+5:30) on the audit machine
(Windows 11, Python 3.12.14) at the v0.6.0 state; first measured 2026-09-09
after the dependency upgrade to Sep-2026 stable. Reproduce with:

```bash
uv run ruff format --check . && uv run ruff check . && uv run ty check
uv run pytest tests/ --cov=. --cov-report=term-missing
```

## Quality gates (measured, this revision)

| Gate | Result |
|---|---|
| `ruff format --check` | clean (41 files) |
| `ruff check` | 0 diagnostics |
| `ty check` | 0 diagnostics |
| `pytest` | 206 passed in 30.6 s (was 124 at audit start, 153 at v0.4.0) |
| Coverage gate (CI: core+db+models+schemas, ≥95%) | 100% (468/468 statements, incl. the v0.6.0 `core/ratelimit.py` + `core/revocation.py`) |

## Coverage, full matrix (pytest-cov 7.1.0, module-name flags)

| Module | Stmts | Miss | Measured | Trustworthy? |
|---|---|---|---|---|
| core/security.py | 66 | 0 | 100% | yes |
| core/ratelimit.py | 42 | 0 | 100% | yes |
| core/revocation.py | 30 | 0 | 100% | yes |
| core/i18n.py | 16 | 0 | 100% | yes |
| core/config.py | 45 | 0 | 100% | yes |
| db/database.py | 12 | 0 | 100% | yes |
| models.py | 77 | 0 | 100% | yes |
| schemas.py | 181 | 0 | 100% | yes |
| main.py | 32 | 8 | 75% | yes (lifespan/`__main__` only) |
| services.py | 510 | 195 | 62% | **undercounted** |
| api.py | 250 | 118 | 53% | **undercounted** |
| ui.py | 359 | 208 | 42% | **undercounted** |
| TOTAL (excl. tests) | 1620 | 529 | 67% | mixed |

### The coverage undercount (A-21)

Symptom: endpoint bodies that demonstrably execute (tests assert on their
responses) are reported as missed lines.

Root-caused with a minimal 14-line repro (Starlette + SQLAlchemy `await
db.execute(...)` over aiosqlite): code **resumed after an await on the
aiosqlite worker thread** is not recorded by coverage.py. Verified NOT
undercounted for: plain asyncio suspensions (`asyncio.sleep`), cross-thread
`run_in_executor`, Starlette alone, FastAPI with yield-dependencies, and
FastAPI+aiosqlite **without** SQLAlchemy. Verified NOT fixed by: Python
3.12.14 → 3.13.15, `COVERAGE_CORE=sysmon`, `COVERAGE_CORE=ctrace`,
`concurrency = greenlet,thread`, coverage 7.13.4 → 7.16.0.

Consequence: line percentages for `api.py`/`services.py`/`ui.py` are
deterministic lower bounds, useful as a regression trend but not as an absolute
measure — hence the CI gate is scoped to the fully-measurable modules
(documented in `docs/style-guides/testing.md`). Tests nonetheless exercise the
undercounted paths behaviorally (REST endpoints, the permission matrix, UI
auth/CSRF flows, upload hardening, login rate limiting, logout revocation).

## Performance characteristics (observed, not benchmarked)

- Heuristic fallback paths are pure in-process computation; full test suite
  (206 tests) runs in ~31 s on 6 cores (measured 2026-09-16).
- AI-enabled paths add one round-trip per LLM call (parse, score, feedback are
  sequential by design); recommendations score up to 100 jobs **sequentially** —
  this is the dominant latency risk with real keys (A-13).
- SQLite via aiosqlite is single-writer; adequate for single-node self-hosting,
  not for concurrent write-heavy use (switch to PostgreSQL).

## Limitations

1. **No DB migrations.** `create_all` only; column changes require manual
   migration (A-28; deferred 2026-09-14 with exact adoption steps recorded in
   docs/STATUS.md).
2. **Match scoring is LLM-dependent for nuance.** Heuristics are coarse
   (set intersection + fixed weights 0.6/0.3/0.1); scores without keys are
   directional, not calibrated.
3. **Heuristic parser is keyword-based.** `AIService._default_resume_payload`
   matches a fixed 26-skill keyword list; resumes outside that vocabulary parse
   poorly without AI keys.
4. **Rate limiting is in-memory and login-only** (A-26, fixed 2026-09-14).
   `POST /api/v1/auth/login` is limited per IP + username (5 / 300 s,
   settings-driven), but the counters are per worker and reset on restart, so
   multi-worker deployments get N× the nominal limit and a restart clears all
   state. Registration is not rate-limited; there is no account lockout. A
   shared store (Redis) is the upgrade path.
5. **Single-node design.** No queue, no horizontal session store. JWT
   revocation exists since 2026-09-14 (A-27: `jti` denylist + logout) but the
   denylist is per worker and cleared on restart — pre-restart revocations
   lapse until the token's own expiry. Cross-worker revocation needs a shared
   store.
6. **Coverage tooling gap** (A-21) as above — reported numbers for the three
   biggest modules are lower bounds.
7. **Windows dev caveat.** aiosqlite's thread-based driver triggers the
   coverage undercount everywhere (not Windows-specific), but local manual
   testing here happens on Windows/VMware; CI (ubuntu) is the reference
   environment for gates.
