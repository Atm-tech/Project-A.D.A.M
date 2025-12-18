from logging.config import fileConfig
import os
from dotenv import load_dotenv

# ---------------------------------------------
# LOAD .env BEFORE ANYTHING ELSE
# ---------------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
env_path = os.path.join(BASE_DIR, ".env")
load_dotenv(env_path)

# ---------------------------------------------
# Alembic + SQLAlchemy imports
# ---------------------------------------------
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.models.base import Base
from app.core.config import settings

config = context.config

# ---------------------------------------------
# DEBUG — SHOW WHAT ALEMBIC IS READING
# ---------------------------------------------
print("\n========== ALEMBIC ENV DEBUG ==========")
print("RAW settings.DATABASE_URL =", settings.DATABASE_URL)

# ---------------------------------------------
# ESCAPE % FOR CONFIGPARSER
# ---------------------------------------------
db_url = settings.DATABASE_URL.replace("%", "%%")
config.set_main_option("sqlalchemy.url", db_url)

print("ESCAPED ALEMBIC URL      =", db_url)
print("========================================\n")

# ---------------------------------------------
# Logging
# ---------------------------------------------
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------
# Target metadata for autogenerate
# ---------------------------------------------
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in live DB mode."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

print("TABLES FOUND IN Base.metadata:", target_metadata.tables.keys())
