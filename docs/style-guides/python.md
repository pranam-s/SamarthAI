# Python Style Guide (summary)

Authoritative sources: [PEP 8](https://peps.python.org/pep-0008/) · [PEP 257](https://peps.python.org/pep-0257/) · [ruff rules](https://docs.astral.sh/ruff/rules/)

This project enforces style mechanically via ruff (`ruff format` + `ruff check`).
The rules below are the human-readable contract; if ruff and this doc disagree,
ruff wins.

## Formatting (enforced by `ruff format`)

- Line length 100; double quotes; 4-space indentation; trailing commas where multiline.
- Imports: `stdlib` → third-party → local, alphabetized within groups (ruff `I`).

## Naming (PEP 8)

- `snake_case` for functions, variables, modules; `PascalCase` for classes;
  `SCREAMING_SNAKE_CASE` for module constants (`EN_TRANSLATIONS`, `ALLOWED_UPLOAD_EXTENSIONS`).
- Avoid shadowing builtins except where an API requires the name
  (`id`, `type` in FastAPI path params are conventional and accepted here).

## Typing

- Full type hints on all function signatures (`def foo(x: int) -> str | None`).
- Modern syntax: `X | None` not `Optional[X]`; `list[str]` not `List[str]`; `dict[str, Any]`.
- `from __future__ import annotations` in test modules; not required elsewhere (Py 3.12).
- Type checking via `ty` is blocking in CI; suppressions must carry a reason
  (`# type: ignore[code]  # reason`) and are audited.

## Docstrings

- Every module, class, and non-trivial public function gets a one-line docstring.
- Imperative mood: """Parse the resume text.""" not """Parses..."""

## Error handling

- Never swallow exceptions silently; log with `logger.exception` and continue or re-raise.
- User-facing errors never embed raw exception text (see AUDIT A-05); map to
  generic messages, keep details server-side.
- Raise `HTTPException` with the most specific status code
  (400 validation, 401 unauthenticated, 403 forbidden, 404 missing, 409 conflict,
  413 too large, 415 unsupported media).

## Dead code

- No commented-out code, no unused schemas/functions. Deletions are preferable
  to "maybe we'll need it".
