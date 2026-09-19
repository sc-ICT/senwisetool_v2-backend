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
    from app.models.form_builder.project import Project
    from app.models.plugin import Plugin
    from app.models.user import User


class PluginProgram(Base):
    """
    Programme métier d'un plugin.

    Un programme peut être :
    - GLOBAL : défini et administré par le plugin / les administrateurs ;
    - USER   : créé et géré par un utilisateur.

    La temporalité est stockée dans `schedule` afin de pouvoir gérer :
    - une seule période ;
    - une récurrence régulière ;
    - des périodes totalement personnalisées.

    La structure du calendrier est validée par les schemas/services.
    """

    __tablename__ = "plugin_programs"

    __table_args__ = (
        UniqueConstraint(
            "plugin_id",
            "key",
            name="uq_plugin_programs_plugin_key",
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

    code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
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

    # ========================================================================
    # PRESENTATION
    # ========================================================================

    icon: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    color: Mapped[str | None] = mapped_column(
        String(50),
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

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="DRAFT",
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    # ========================================================================
    # OWNERSHIP / SCOPE
    # ========================================================================

    scope: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="GLOBAL",
        index=True,
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    owner_user_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
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

    allow_multiple_projects: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    allow_project_creation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # ========================================================================
    # CONFIGURATION
    # ========================================================================

    configuration: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    project_rules: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    resource_bindings: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    # ========================================================================
    # CALENDAR
    # ========================================================================

    schedule: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    # ========================================================================
    # DATES
    # ========================================================================

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

    created_by_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by],
        lazy="raise",
    )

    owner_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[owner_user_id],
        lazy="raise",
    )

    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="program",
        foreign_keys="Project.program_id",
        lazy="selectin",
    )
