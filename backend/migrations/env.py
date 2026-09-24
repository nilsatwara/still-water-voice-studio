"""Async PostgreSQL Alembic environment driven only by backend settings."""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from backend.app.core.config import settings
from backend.app.models import Base


config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

if not settings.database_url:
    raise RuntimeError('DATABASE_URL is required to run database migrations.')

# ConfigParser treats percent signs as interpolation, so escaped credentials
# must be doubled when the URL is injected programmatically.
config.set_main_option('sqlalchemy.url', settings.database_url.replace('%', '%%'))
target_metadata = Base.metadata


def migration_options() -> dict:
    return {
        'target_metadata': target_metadata,
        'compare_type': True,
        'compare_server_default': True,
        'transaction_per_migration': True,
    }


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option('sqlalchemy.url'),
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
        **migration_options(),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_sync_migrations(connection: Connection) -> None:
    context.configure(connection=connection, **migration_options())
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )
    try:
        async with engine.connect() as connection:
            await connection.run_sync(run_sync_migrations)
    finally:
        await engine.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
