"""
migrations/env.py

Alembic's entry point. We override the default to:
1. Read the DATABASE_URL from our .env file (not alembic.ini)
2. Import all our models so Alembic can detect schema changes automatically
"""

import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Load Alembic config object (reads alembic.ini)
config = context.config

# Setup Python logging from the ini file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

import sys
from os.path import abspath, dirname

# This adds the parent directory of 'migrations' to your search path
sys.path.insert(0, dirname(dirname(abspath(__file__))))

from app.db.base import Base  # Now this will work!

# --- Import Base and ALL models so Alembic can see the full schema ---
# If you add a new model file, import it here too
from app.db.base import Base
from app.models import goal, task_chunk, status_history   # noqa: F401

target_metadata = Base.metadata

# --- Override sqlalchemy.url with value from our .env file ---
from app.core.config import settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates SQL script)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a live DB connection (actually modifies the DB)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()