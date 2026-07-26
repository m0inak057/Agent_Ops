"""Alembic migration environment configuration.

Configures the migration context to use the project's SQLAlchemy models
and database URL for autogeneration and running migrations.
"""

from alembic import context

config = context.config


def run_migrations_offline():
    """Run migrations in 'offline' mode, emitting SQL without a live connection."""
    pass


def run_migrations_online():
    """Run migrations in 'online' mode using a live database connection."""
    pass


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
