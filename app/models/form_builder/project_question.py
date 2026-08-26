from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database import Base

if TYPE_CHECKING:
    from app.models.form_builder.project_definition import (
        ProjectDefinition,
    )
    from app.models.form_builder.project_section import (
        ProjectSection,
    )
    from app.models.form_builder.question_definition import (
        QuestionDefinition,
    )
    from app.models.form_builder.question_version import (
        QuestionVersion,
    )


class ProjectQuestion(Base):
    __tablename__ = "project_questions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    project_id: Mapped[int] = mapped_column(
        ForeignKey(
            "project_definitions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    section_id: Mapped[int] = mapped_column(
        ForeignKey(
            "project_sections.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    question_definition_id: Mapped[int] = mapped_column(
        ForeignKey(
            "question_definitions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    question_version_id: Mapped[int] = mapped_column(
        ForeignKey(
            "question_versions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    position: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    config: Mapped[dict] = mapped_column(
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
        onupdate=func.now(),
        nullable=False,
    )

    project: Mapped["ProjectDefinition"] = relationship(
        "ProjectDefinition",
        lazy="raise",
    )

    section: Mapped["ProjectSection"] = relationship(
        "ProjectSection",
        back_populates="questions",
        lazy="raise",
    )

    question_definition: Mapped["QuestionDefinition"] = relationship(
        "QuestionDefinition",
        lazy="raise",
    )

    question_version: Mapped["QuestionVersion"] = relationship(
        "QuestionVersion",
        lazy="raise",
    )
