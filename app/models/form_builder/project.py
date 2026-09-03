from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.file_node import FileNode
from app.models.form_builder.enums import ProjectStatus

if TYPE_CHECKING:
    from app.models.form_builder.form_definition import FormDefinition
    from app.models.project_agent_assignment import ProjectAgentAssignment
    from app.models.user import User


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
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
    )

    status: Mapped[ProjectStatus] = mapped_column(
        Enum(
            ProjectStatus,
            name="project_status",
        ),
        nullable=False,
        default=ProjectStatus.DRAFT,
        index=True,
    )

    global_config: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    parent_folder_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "file_nodes.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    project_folder_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "file_nodes.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        unique=True,
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

    # ============================================================
    # Relations
    # ============================================================

    created_by_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by],
        lazy="raise",
    )

    forms: Mapped[list["FormDefinition"]] = relationship(
        "FormDefinition",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    agent_assignments: Mapped[list["ProjectAgentAssignment"]] = relationship(
        "ProjectAgentAssignment",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    parent_folder: Mapped["FileNode | None"] = relationship(
        "FileNode",
        foreign_keys=[parent_folder_id],
        lazy="raise",
    )

    project_folder: Mapped["FileNode | None"] = relationship(
        "FileNode",
        foreign_keys=[project_folder_id],
        lazy="raise",
    )
