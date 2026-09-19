from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.plugin import Plugin
    from app.models.plugin_program import PluginProgram
    from app.models.user import User


class PluginProjectTemplate(Base):
    __tablename__ = "plugin_project_templates"

    __table_args__ = (
        UniqueConstraint(
            "plugin_id",
            "key",
            name="uq_plugin_project_templates_plugin_key",
        ),
    )

    # ========================================================================
    # IDENTIFICATION
    # ========================================================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    plugin_id: Mapped[int] = mapped_column(
        ForeignKey(
            "plugins.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    project_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    # ========================================================================
    # PROGRAMME
    # ========================================================================

    program_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "plugin_programs.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # ========================================================================
    # PRESENTATION
    # ========================================================================

    icon: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # ========================================================================
    # LIFECYCLE
    # ========================================================================

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    # ========================================================================
    # PERMISSIONS
    # ========================================================================

    allow_user_use: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    allow_user_customization: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # ========================================================================
    # CONFIGURATION
    # ========================================================================

    configuration: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    rules: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    resource_bindings: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    metrics: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    # ========================================================================
    # AUDIT
    # ========================================================================

    created_by: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ========================================================================
    # RELATIONS
    # ========================================================================

    plugin: Mapped["Plugin"] = relationship(
        "Plugin",
        foreign_keys=[plugin_id],
        lazy="raise",
    )

    program: Mapped["PluginProgram | None"] = relationship(
        "PluginProgram",
        foreign_keys=[program_id],
        lazy="raise",
    )

    created_by_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by],
        lazy="raise",
    )
