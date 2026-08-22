from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import (
    create_async_engine,
)

from alembic import context
from app.database import (
    ASYNC_DATABASE_URL,
    DATABASE_CONNECT_ARGS,
    Base,
)

# Import explicite de tous les modèles
# afin qu'ils soient enregistrés dans Base.metadata.
from app.models.file_node import FileNode
from app.models.form_builder.question_definition import (
    QuestionDefinition,
)
from app.models.form_builder.question_option import (
    QuestionOption,
)
from app.models.form_builder.question_version import (
    QuestionVersion,
)
from app.models.user import User

# ============================================================================
# CONFIGURATION ALEMBIC
# ============================================================================

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ============================================================================
# MODE OFFLINE
# ============================================================================


def run_migrations_offline() -> None:
    """
    Exécute Alembic sans connexion directe à la base.

    Cette fonction utilise la même URL normalisée que l'application.
    """

    context.configure(
        url=ASYNC_DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
    )

    with context.begin_transaction():
        context.run_migrations()


# ============================================================================
# MODE ONLINE
# ============================================================================


def do_run_migrations(
    connection: Connection,
) -> None:
    """
    Configure Alembic à partir d'une connexion SQLAlchemy existante.
    """

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Crée le moteur Alembic avec exactement la même configuration
    PostgreSQL que l'application.
    """

    connectable = create_async_engine(
        ASYNC_DATABASE_URL,
        poolclass=pool.NullPool,
        connect_args=DATABASE_CONNECT_ARGS,
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(
                do_run_migrations,
            )

    finally:
        await connectable.dispose()


# ============================================================================
# POINT D'ENTRÉE
# ============================================================================


def run_migrations_online() -> None:
    asyncio.run(
        run_async_migrations(),
    )


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
