import asyncio
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import create_engine

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
sys.path.insert(0, '')  # Ensure project root is on path
from src.common.config import settings
from src.common.db import Base

target_metadata = Base.metadata


def get_url():
    return settings.DATABASE_URL


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    If the project's DATABASE_URL uses an async driver (for example
    'postgresql+asyncpg://...'), Alembic's sync `create_engine` will not accept it.
    Convert to a sync driver URL by stripping '+asyncpg' when present.
    """
    raw_url = get_url()
    # If using the asyncpg driver, Alembic needs a sync URL for create_engine
    sync_url = raw_url.replace("+asyncpg", "") if raw_url else raw_url
    connectable = create_engine(sync_url)

    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
