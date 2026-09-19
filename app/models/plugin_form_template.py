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
    from app.models.plugin_project_template import PluginProjectTemplate
    from app.models.user import User


class PluginFormTemplate(Base):
    __tablename__ = "plugin_form_templates"

    __table_args__ = (
        UniqueConstraint(
            "project_template_id",
            "key",
            name="uq_plugin_form_templates_project_template_key",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    project_template_id: Mapped[int] = mapped_column(
        ForeignKey(
            "plugin_project_templates.id",
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

    form_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    min_instances: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    max_instances: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

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

    global_config: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    definition: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    resource_bindings: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    rules: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    metrics: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

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

    project_template: Mapped["PluginProjectTemplate"] = relationship(
        "PluginProjectTemplate",
        lazy="raise",
    )

    created_by_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by],
        lazy="raise",
    )
