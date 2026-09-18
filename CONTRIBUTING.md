# Contributing

Thanks for considering a contribution. Samarth AI is a portfolio project, so
review may be slow, but the bar for every change is the same one the codebase
already holds itself to.

## Ground rules

- Accessibility is not optional. The UI is semantic HTML with keyboard
  navigation, visible focus, and a skip link; every user-facing string goes
  through the `t(key)` i18n pipeline. If your change adds UI, it works with a
  keyboard and a screen reader or it does not land.
- No hacks: no placeholders, no stubs treated as done, no suppressed
  warnings. If a lint or type rule fires, fix the cause or open an issue
  explaining why the rule is wrong for that site.
- Root-cause fixes only. A test that fails signals something; find out what.

## Setup

```bash
uv sync --all-groups
cp .env.example .env   # optional; the app runs keyless with heuristics
uv run uvicorn main:app --reload
```

## Schema changes

Models in `models.py` are the source of truth. Any change to existing tables
lands as an Alembic revision:

```bash
uv run alembic revision --autogenerate -m "describe the change"
# review the generated ops, then verify both directions:
uv run alembic upgrade head
uv run alembic downgrade -1 && uv run alembic upgrade head
```

`create_all` at startup is a dev convenience for fresh databases only; do not
rely on it for changes to existing tables (see docs/ADR/0001).

## Quality gates (all required before a commit)

```bash
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest tests/ --cov=core --cov=db --cov=models --cov=schemas --cov-fail-under=95
```

Coverage on `core/`, `db/`, `models.py`, and `schemas.py` is gated at 95% in
CI and currently sits at 100%. New UI strings need keys in EN and all 19
locale overrides (tests will catch a missing one).

## Commit style

Conventional commits: `feat:`, `fix:`, `test:`, `docs:`, `chore(deps):`,
`ci:`. One logical change per commit.

## Reporting issues

Include what you ran, what you expected, and what happened. For security
issues, do not open a public issue; use GitHub's private security advisory
for the repository.
