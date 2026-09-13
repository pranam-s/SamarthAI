# Status — honest state

Updated: 2026-09-14 (IST), audit-remediation pass on top of `d6edf2b`.

## What works right now (verified this session)

- Full quality gates green on Windows/Py 3.12.14: ruff format+lint, ty, 180/180 tests.
- Gated coverage (core/, db/, models.py, schemas.py) still 100%; reported-only
  modules re-measured (api 51%, services 62%, ui 41% — undercounted, A-21).
- The documented multi-target pytest-cov command works again (A-25 fix).
- All REST endpoints, UI auth/CSRF flows, locale switching, and upload
  hardening are behavior-tested (tests/test_api.py, test_ui.py, test_services.py).
- Works with zero AI keys: heuristic parse/match/feedback/skills-gap paths all
  covered by tests.

## Changes in this pass (11 commits, local only — NOT pushed per owner directive)

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

## Known open items (tracked in docs/AUDIT.md)

- **Medium**: sequential AI scoring in recommendations (A-13 — needs product
  input before batching/persistence decisions).
- **Low**: models.py `String` column lengths (A-19).
- **Infra**: Alembic migrations (none today), login rate limiting, JWT
  revocation story, coverage.py undercount upstream (A-21; a coverage.py
  issue would be the right home).
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
(180/180 tests; gated coverage 100%).
