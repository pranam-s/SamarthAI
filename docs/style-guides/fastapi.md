# FastAPI Conventions (summary)

Authoritative sources: [FastAPI docs](https://fastapi.tiangolo.com/) ·
[SQLAlchemy 2.0 ORM style](https://docs.sqlalchemy.org/en/20/orm/quickstart.html) ·
[Pydantic v2 docs](https://docs.pydantic.dev/latest/)

## Layer boundaries (this project)

```
api.py (REST)  ─┐
ui.py (SSR)    ─┼─→ services.py (domain + AI) → models.py (ORM) → db/database.py
schemas.py (I/O contracts)
```

- Route modules do: auth, permission checks, validation (via schemas), and
  response shaping. No raw SQL, no business logic, no AI calls.
- `services.py` owns all business logic and AI provider interaction; returns
  ORM models or plain dicts; may raise `HTTPException` for client errors.
- `core/security.py` is the only place that touches bcrypt/JWT/CSRF primitives.

## Routes

- Annotated dependency injection: `current_user: Annotated[User, Depends(get_current_user)]`.
- Router-level prefixes (`settings.API_V1_STR`); one router per surface (API vs UI).
- Status codes: explicit `status.HTTP_*` constants; `303 SEE OTHER` for UI form
  redirects after POST (PRG pattern).
- Every list endpoint takes `skip`/`limit` (defaults 0/100).
- CSRF: every authenticated UI form POST validates `csrf_token` first thing
  (`validate_csrf_or_400`).

## Schemas (Pydantic v2)

- `model_config = ConfigDict(from_attributes=True)` on response models read from ORM.
- Response models set explicitly via `response_model=` — never return raw ORM
  objects without one.
- Nullable ORM columns must have `= None` (or a default) in schemas.
- Prefer `Literal[...]` unions over free `str` for enumerated values
  (`job_type`, `experience_level`).

## Async / DB

- SQLAlchemy 2.0 `Mapped[...]`/`mapped_column` style only.
- Sessions come only from `get_db`; one session per request; commit + refresh in services.
- AI provider calls that are sync (OpenAI SDK) go through `asyncio.to_thread`.
- Never block the loop with file or network IO: use `aiofiles` / async clients.

## Security invariants (do not regress)

- `httponly=True` auth cookies; `COOKIE_SECURE`/`COOKIE_SAMESITE` from settings.
- bcrypt direct (no passlib); JWT HS256 via PyJWT; `sub` is always a string; parse to int at the boundary.
- CORS from `settings.CORS_ORIGINS`, never `"*"` in production.
- Redirect targets from user input must be same-origin relative paths.
- Uploads: extension allow-list + streaming size cap.
