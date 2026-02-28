# agents.md

## Purpose
Defines how AI coding agents should contribute to this repository safely and consistently.

## Standards

- Prefer minimal, root-cause fixes over surface patches.
- Keep architecture simple: FastAPI + Jinja SSR + service layer.
- Maintain Python 3.12 compatibility.
- Use `uv` for dependency and environment management.
- Run quality gates before proposing completion: `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`, `uv run pytest`.

## Security Rules

- Never log secrets or tokens.
- Preserve secure auth behavior (cookie flags + token validation + CSRF checks for authenticated form writes).
- Keep environment-specific settings in `.env` and `core/config.py`.

## i18n and Accessibility

- Keep user-facing text translatable through context translation helpers.
- Prefer semantic HTML and keyboard-accessible controls.
- Ensure forms have labels and clear submit controls.

## AI Integrations

- Primary provider: Google GenAI.
- Fallback provider: OpenRouter.
- Ensure functional degradation when provider keys are missing.

## Contribution Flow

1. Read impacted files.
2. Update service and route contracts together.
3. Update templates if endpoint/form behavior changes.
4. Run tests/lint/type checks.
5. Update docs if behavior changes.
