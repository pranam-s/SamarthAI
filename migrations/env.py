"""Alembic migration environment.

Wired to the application's own configuration: the database URL comes from
``core.config.settings`` (so secrets stay in `.env`, never in alembic.ini)
and the migration target is ``models.Base.metadata`` (models are the source
of truth, per ADR-0001). The engine is built with the async recipe from the
Alembic cookbook because both supported drivers (aiosqlite, asyncpg) are
async.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

import models
from core.config import settings

# `models` is imported for its registration side effect: defining the ORM
# classes is what attaches the four tables to the shared declarative Base
# (models.Base is db.database.Base). target_metadata references it through
# the module so the side-effect import is not flagged as unused.

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The URL lives in settings (.env); alembic.ini intentionally carries none.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = models.Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL; emits SQL to the script output
    instead of touching a database.
    """
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode over an async engine."""
    import asyncio

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
