# Evaluation & Limitations

All numbers below were measured on 2026-09-09 (UTC+5:30) on the audit machine
(Windows 11, Python 3.12.14, uv 0.12.10) after the dependency upgrade to
Sep-2026 stable. Reproduce with:

```bash
uv run ruff format --check . && uv run ruff check . && uv run ty check
uv run pytest tests/ --cov=. --cov-report=term-missing
```

## Quality gates (measured, this revision)

| Gate | Result |
|---|---|
| `ruff format --check` | clean (29 files) |
| `ruff check` | 0 diagnostics |
| `ty check` | 0 diagnostics |
| `pytest` | 153 passed (was 124 at audit start) |
| Coverage gate (CI: core+db+models+schemas, ≥95%) | 100% (108/108 statements) |

## Coverage, full matrix (pytest-cov 7.1.0)

| Module | Stmts | Miss | Measured | Trustworthy? |
|---|---|---|---|---|
| core/security.py | 39 | 0 | 100% | yes |
| core/i18n.py | 16 | 0 | 100% | yes |
| core/config.py | 41 | 0 | 100% | yes |
| db/database.py | 12 | 0 | 100% | yes |
| models.py | 77 | 0 | 100% | yes |
| schemas.py | 220 | 0 | 100% | yes |
| main.py | 31 | 8 | 74% | yes (lifespan/`__main__` only) |
| services.py | 487 | 197 | 60% | **undercounted** |
| api.py | 246 | 123 | 50% | **undercounted** |
| ui.py | 368 | 244 | 34% | **undercounted** + real gaps |
| TOTAL (excl. tests) | 1537 | 572 | 63% | mixed |

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
undercounted paths behaviorally (153 tests cover every REST endpoint,
permission matrix, UI auth/CSRF flows, and upload hardening).

## Performance characteristics (observed, not benchmarked)

- Heuristic fallback paths are pure in-process computation; full test suite
  (153 tests incl. ~60 HTTP round-trips) runs in ~21 s on 6 cores.
- AI-enabled paths add one round-trip per LLM call (parse, score, feedback are
  sequential by design); recommendations score up to 100 jobs **sequentially** —
  this is the dominant latency risk with real keys (A-13).
- SQLite via aiosqlite is single-writer; adequate for single-node self-hosting,
  not for concurrent write-heavy use (switch to PostgreSQL).

## Limitations

1. **No DB migrations.** `create_all` only; column changes require manual
   migration (Alembic adoption is the top infra TODO).
2. **Match scoring is LLM-dependent for nuance.** Heuristics are coarse
   (set intersection + fixed weights 0.6/0.3/0.1); scores without keys are
   directional, not calibrated.
3. **Heuristic parser is keyword-based.** `AIService._default_resume_payload`
   matches a fixed 26-skill keyword list; resumes outside that vocabulary parse
   poorly without AI keys.
4. **Localization of dynamic errors.** Route-level error strings in `ui.py`
   bypass the `t()` pipeline (A-09); templates are translated, server
   validation messages are English-only.
5. **No rate limiting / account lockout** on login or registration endpoints.
6. **Single-node design.** No queue, no horizontal session store; JWTs are
   stateless (no revocation beyond expiry — 5-day default).
7. **Coverage tooling gap** (A-21) as above — reported numbers for the three
   biggest modules are lower bounds.
8. **Windows dev caveat.** aiosqlite's thread-based driver triggers the
   coverage undercount everywhere (not Windows-specific), but local manual
   testing here happens on Windows/VMware; CI (ubuntu) is the reference
   environment for gates.
