"""Explicit reviewed migrations only until Phase 1 has full ORM model coverage."""

import os

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import get_settings

url = os.environ.get("MIGRATION_DATABASE_URL") or get_settings().database_url.get_secret_value()


def reject_autogenerate(_ctx, _revision, _directives):
    if getattr(context.config.cmd_opts, "autogenerate", False):
        raise RuntimeError(
            "Phase 0 has only the User ORM model. Write explicit migrations until Phase 1 maps all tables."
        )


if context.is_offline_mode():
    context.configure(url=url, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()
else:
    with create_engine(url, poolclass=pool.NullPool).connect() as connection:
        context.configure(connection=connection, process_revision_directives=reject_autogenerate)
        with context.begin_transaction():
            context.run_migrations()
