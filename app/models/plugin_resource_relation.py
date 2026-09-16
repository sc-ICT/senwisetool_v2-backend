from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.plugin import PluginResource


class PluginResourceRelation(Base):
    """
    Relation entre deux ressources d'un même plugin.

    Exemple :

        PLANTATION.code_planteur
                    ↓
        PLANTEUR.code

    La ressource source contient la référence.
    La ressource cible contient la valeur référencée.

    Une relation est orientée, mais peut être parcourue dans les deux sens.
    """

    __tablename__ = "plugin_resource_relations"

    __table_args__ = (
        UniqueConstraint(
            "source_resource_id",
            "source_field_key",
            "target_resource_id",
            "target_field_key",
            name="uq_plugin_resource_relation_fields",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    source_resource_id: Mapped[int] = mapped_column(
        ForeignKey(
            "plugin_resources.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    source_field_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    target_resource_id: Mapped[int] = mapped_column(
        ForeignKey(
            "plugin_resources.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    target_field_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    label: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
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

    source_resource: Mapped["PluginResource"] = relationship(
        "PluginResource",
        foreign_keys=[source_resource_id],
        back_populates="outgoing_relations",
        lazy="raise",
    )

    target_resource: Mapped["PluginResource"] = relationship(
        "PluginResource",
        foreign_keys=[target_resource_id],
        back_populates="incoming_relations",
        lazy="raise",
    )
