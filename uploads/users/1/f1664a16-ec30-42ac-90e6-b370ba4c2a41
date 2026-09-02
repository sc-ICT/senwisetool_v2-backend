from __future__ import annotations

from collections.abc import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


def _normalize_database_url(
    raw_url: str,
) -> tuple[str, dict]:
    """
    Normalise une URL PostgreSQL destinée à SQLAlchemy + asyncpg.

    L'URL peut venir de n'importe quel fournisseur PostgreSQL.

    Les paramètres spécifiques au client PostgreSQL comme :
    - sslmode
    - channel_binding

    ne sont pas transmis directement à asyncpg.

    sslmode est utilisé pour construire le contexte SSL.
    """

    if not raw_url or not raw_url.strip():
        raise RuntimeError("DATABASE_URL n'est pas configurée.")

    database_url = make_url(raw_url.strip())

    # ------------------------------------------------------------------
    # Driver
    # ------------------------------------------------------------------

    if database_url.drivername in {
        "postgresql",
        "postgres",
    }:
        database_url = database_url.set(
            drivername="postgresql+asyncpg",
        )

    elif database_url.drivername != "postgresql+asyncpg":
        raise RuntimeError(
            "DATABASE_URL doit utiliser PostgreSQL. " f"Driver reçu : {database_url.drivername}"
        )

    # ------------------------------------------------------------------
    # Paramètres de connexion
    # ------------------------------------------------------------------

    query = dict(database_url.query)

    sslmode = query.pop(
        "sslmode",
        None,
    )

    # asyncpg ne supporte pas channel_binding
    # comme argument de connexion.
    query.pop(
        "channel_binding",
        None,
    )

    database_url = database_url.set(
        query=query,
    )

    # ------------------------------------------------------------------
    # SSL
    # ------------------------------------------------------------------

    connect_args: dict = {}

    if sslmode in {
        "require",
        "verify-ca",
        "verify-full",
    }:
        import ssl

        ssl_context = ssl.create_default_context()

        if sslmode == "require":
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        elif sslmode == "verify-ca":
            ssl_context.check_hostname = False

        connect_args["ssl"] = ssl_context

    return (
        database_url.render_as_string(
            hide_password=False,
        ),
        connect_args,
    )


# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

ASYNC_DATABASE_URL, DATABASE_CONNECT_ARGS = _normalize_database_url(
    settings.DATABASE_URL,
)


# ============================================================================
# SQLALCHEMY ENGINE
# ============================================================================

engine: AsyncEngine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=settings.is_development,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args=DATABASE_CONNECT_ARGS,
)


# ============================================================================
# SESSION FACTORY
# ============================================================================

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ============================================================================
# SQLALCHEMY BASE
# ============================================================================


class Base(DeclarativeBase):
    """
    Classe de base commune à tous les modèles SQLAlchemy.
    """

    pass


# ============================================================================
# FASTAPI DATABASE DEPENDENCY
# ============================================================================


async def get_db() -> AsyncGenerator[
    AsyncSession,
    None,
]:
    """
    Fournit une session SQLAlchemy à FastAPI.

    La session est commitée si tout s'est bien déroulé,
    rollbackée en cas d'erreur, puis toujours fermée.
    """

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()

        except Exception:
            await session.rollback()
            raise
