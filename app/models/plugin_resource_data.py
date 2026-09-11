from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.plugin import PluginResource
    from app.models.user import User


class PluginResourceRecord(Base):
    """
    Donnée d'une ressource.

    GLOBAL resource:
        user_id = NULL
        → donnée commune à tous les utilisateurs.

    USER resource:
        user_id = NULL
        → donnée créée par l'admin et commune à tous.

        user_id != NULL
        → donnée appartenant exclusivement à cet utilisateur.
    """

    __tablename__ = "plugin_resource_records"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    resource_id: Mapped[int] = mapped_column(
        ForeignKey(
            "plugin_resources.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    user_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
    )

    resource: Mapped["PluginResource"] = relationship(
        "PluginResource",
        lazy="raise",
    )

    user: Mapped["User | None"] = relationship(
        "User",
        lazy="raise",
    )


class PluginResourceUserSchema(Base):
    """
    Override du schema d'une ressource USER.

    Le schema administrateur reste dans PluginResource/PluginResourceField.

    Cette table contient uniquement la personnalisation propre
    à un utilisateur.
    """

    __tablename__ = "plugin_resource_user_schemas"

    __table_args__ = (
        UniqueConstraint(
            "resource_id",
            "user_id",
            name="uq_plugin_resource_user_schema_resource_user",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    resource_id: Mapped[int] = mapped_column(
        ForeignKey(
            "plugin_resources.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    schema_definition: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now(),
        nullable=False,
    )

    resource: Mapped["PluginResource"] = relationship(
        "PluginResource",
        lazy="raise",
    )

    user: Mapped["User"] = relationship(
        "User",
        lazy="raise",
    )
