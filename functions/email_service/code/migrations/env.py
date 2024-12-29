# ruff:noqa: ARG001
import asyncio
from code.db import db_secret

# All models must be imported here
from code.models import *  # noqa: F403
from logging.config import fileConfig
from typing import Literal

from alembic import context
from sqlalchemy.engine.base import Connection
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import SchemaItem
from sqlmodel import SQLModel, text


SCHEMA_NAME = "email"

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def include_object(
    object: SchemaItem,
    name: str | None,
    type: Literal[
        "schema",
        "table",
        "column",
        "index",
        "unique_constraint",
        "foreign_key_constraint",
    ],
    reflected: bool,
    compare_to: SchemaItem | None,
) -> bool:
    """Select which objects will be included in the migration.

    For example, to exclude indexes, you can use the following code:

        ```python
        if _type == "index":
            return False
        return True
        ```
    """
    return True


def do_run_migrations(connection: Connection) -> None:
    """Run migrations"""
    connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME};"))
    connection.commit()
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        version_table_schema=SCHEMA_NAME,
        include_schemas=False,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an Engine and associate a connection with the context and run async migrations"""
    try:
        engine = create_async_engine(
            url=URL.create(**db_secret),
        )

        async with engine.connect() as connection:
            await connection.run_sync(do_run_migrations)
    except Exception:  # noqa: BLE001
        db_secret["host"] = "localhost"
        engine = create_async_engine(
            url=URL.create(**db_secret),
        )

        async with engine.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await engine.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = config.attributes.get("connection")

    if not connectable:
        if asyncio.get_event_loop().is_running():
            coroutine = run_async_migrations()
            asyncio.create_task(coroutine)  # noqa: RUF006
        else:
            asyncio.run(run_async_migrations())
    else:
        context.configure(
            connection=connectable,
            target_metadata=target_metadata,
            include_object=include_object,
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
