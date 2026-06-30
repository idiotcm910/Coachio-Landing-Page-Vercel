from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.base import Base  # noqa: E402
import app.models  # noqa: F401, E402  — registers all funnel tables on Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Neon transaction-pooler can't run all DDL → prefer non-pooling URL for Alembic;
# runtime app still uses the pooled DATABASE_URL.
# Priority: DATABASE_URL_UNPOOLED → POSTGRES_URL_NON_POOLING (Vercel-Neon)
#         → DATABASE_URL → POSTGRES_URL (Vercel-Neon pooled, last resort)
_db_url = (
    os.getenv("DATABASE_URL_UNPOOLED")
    or os.getenv("POSTGRES_URL_NON_POOLING")
    or os.getenv("DATABASE_URL")
    or os.getenv("POSTGRES_URL")
)
# Normalize scheme: SQLAlchemy requires 'postgresql://', not 'postgres://'
if _db_url and _db_url.startswith("postgres://"):
    _db_url = "postgresql://" + _db_url[len("postgres://"):]
if _db_url:
    config.set_main_option("sqlalchemy.url", _db_url)


def run_migrations_offline() -> None:
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
