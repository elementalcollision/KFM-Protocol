import asyncio
from logging.config import fileConfig
import os
import sys

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# This allows alembic to find your models
# Add the project root directory to the path
project_root = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

# Import Base from your models directory using absolute path now
from f_operator_service.db.base import Base
# Import your actual models so Base has them registered
from f_operator_service.models.experiment import Experiment # Use absolute import
from f_operator_service.models.provenance import ProvenanceRecord # Import ProvenanceRecord model

# Import settings to get the database URL
from f_operator_service.core.config import get_settings # Use absolute import

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line needs to be adapted for the new logging config file
if config.config_file_name:
    logging_config_path = os.path.join(os.path.dirname(config.config_file_name), config.get_main_option('logging_config_file', 'alembic_log.ini'))
    if os.path.exists(logging_config_path):
        fileConfig(logging_config_path)
    else:
        print(f"Warning: Logging config file {logging_config_path} not found.")

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:_BASE
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

# Set the database URL from application settings
db_settings = get_settings()
if db_settings.SQLALCHEMY_DATABASE_URI_F:
    config.set_main_option("sqlalchemy.url", db_settings.SQLALCHEMY_DATABASE_URI_F)
else:
    print("Error: SQLALCHEMY_DATABASE_URI_F is not set in the configuration.")
    sys.exit(1) # Exit if DB URI is missing

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In async mode, provide an AsyncEngine or AsyncConnection
    and pass it to the context.configure() call.

    """

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
