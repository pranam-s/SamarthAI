# Status — honest state

Updated: 2026-09-09 (IST), post-improvement pass on top of `ec017a9`.

## What works right now (verified this session)

- Full quality gates green on Windows/Py 3.12.14: ruff format+lint, ty, 153/153 tests.
- CI pipeline defined for lint → type check → tests with a 95% coverage gate on
  core modules (measured 100%) → docker smoke test. NOTE: CI has not run on
  GitHub yet — the owner does not want these commits pushed; the workflow file
  is exercised only by an equivalent local run of each step.
- All REST endpoints, UI auth/CSRF flows, locale switching, and upload
  hardening are behavior-tested (tests/test_api.py, test_ui.py, test_services.py).
- Works with zero AI keys: heuristic parse/match/feedback/skills-gap paths all
  covered by tests.

## Changes in this pass (8 commits, local only — NOT pushed per owner directive)

1. `docs`: full audit `docs/AUDIT.md` (23 findings).
2. `fix(security)`: upload size cap + extension whitelist (413/415), open-redirect fix on `/set-locale`, JWT `sub` int parsing in UI, no raw exception text in pages, job-edit skill-wipe bug, `.env.example` restored (was swallowed by `.gitignore`), new-style TemplateResponse.
3. `chore(deps)`: every dependency to Sep-2026 stable — fastapi 0.141.1 (starlette 1.6), pydantic 2.13.5, sqlalchemy 2.0.52, uvicorn 0.52.4, google-genai 2.22 (major), openai 3.9 (major), pyjwt 2.13, pytest 9.1, ruff 0.16.6, ty 0.0.79; pyjwt extra name fixed.
4. `test`: +29 tests (config, database, security decode/expiry, UI flows, upload hardening).
5. `ci`: blocking type check, coverage gate, README badge.
6. `docs`: style guides, agents.md rewrite, PRD/ARCHITECTURE/EVALUATION/STATUS, README accuracy fixes.

## Known open items (tracked in docs/AUDIT.md)

- **High value, low effort**: min password length (A-10), 401-vs-403/409 status
  semantics (A-08), locale-list dedup (A-11).
- **Medium**: i18n for dynamic error strings (A-09), dead schemas (A-12),
  sequential AI scoring in recommendations (A-13), private-member access (A-14),
  UI applications-list ad-hoc attributes (A-15), token-decode duplication (A-16).
- **Infra**: Alembic migrations (none today), login rate limiting, JWT
  revocation story, coverage.py undercount upstream
  ([fastapi discussion #8750](https://github.com/fastapi/fastapi/discussions/8750) is
  adjacent; a coverage.py issue would be the right home).

## Verification commands

```bash
uv sync --all-groups
uv run ruff format --check . && uv run ruff check . && uv run ty check
uv run pytest tests/ -v --cov=core --cov=db --cov=models.py --cov=schemas.py --cov-fail-under=95
```

All four lines were run and green immediately before this file was committed.
