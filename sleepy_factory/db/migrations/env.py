from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

from sleepy_factory.db.models import Base

# Ensure project root is importable when Alembic runs from repo root.
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.append(str(REPO_ROOT))

config = context.config


def _set_sqlalchemy_url_from_env() -> None:
    try:
        from sleepy_factory.config import settings
    except Exception as exc:
        # Make Alembic fail with a clean, user-facing message.
        raise SystemExit(str(exc)) from exc

    config.set_main_option("sqlalchemy.url", settings.database_url)


_set_sqlalchemy_url_from_env()

# Configure Python logging using alembic.ini.
if config.config_file_name:
    fileConfig(config.config_file_name)

# Target metadata for `alembic revision --autogenerate`.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without a DB connection (emits SQL to the script output)."""
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
    """Run migrations with a live DB connection."""
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
