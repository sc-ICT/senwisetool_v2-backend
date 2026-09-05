from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.file_node import FileNode
from app.models.form_builder.enums import FormStatus

if TYPE_CHECKING:
    from app.models.form_builder.form_section import FormSection
    from app.models.form_builder.project import Project
    from app.models.submission import Submission
    from app.models.user import User


class FormDefinition(Base):
    __tablename__ = "form_definitions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
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

    form_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    status: Mapped[FormStatus] = mapped_column(
        Enum(
            FormStatus,
            name="form_status",
        ),
        nullable=False,
        default=FormStatus.DRAFT,
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

    project_id: Mapped[int] = mapped_column(
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    form_folder_id: Mapped[int | None] = mapped_column(
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

    created_by_user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by],
        lazy="raise",
    )

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="forms",
        lazy="raise",
    )

    sections: Mapped[list["FormSection"]] = relationship(
        "FormSection",
        back_populates="form",
        cascade="all, delete-orphan",
        order_by="FormSection.position",
        lazy="selectin",
    )

    form_folder: Mapped["FileNode | None"] = relationship(
        "FileNode",
        foreign_keys=[form_folder_id],
        lazy="raise",
    )

    submissions: Mapped[list["Submission"]] = relationship(
        "Submission",
        back_populates="form",
        lazy="selectin",
    )
