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
    from app.models.form_builder.form_definition import (
        FormDefinition,
    )
    from app.models.form_builder.form_section import (
        FormSection,
    )
    from app.models.form_builder.question_definition import (
        QuestionDefinition,
    )
    from app.models.form_builder.question_version import (
        QuestionVersion,
    )


class FormQuestion(Base):
    __tablename__ = "form_questions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    form_id: Mapped[int] = mapped_column(
        ForeignKey(
            "form_definitions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    section_id: Mapped[int] = mapped_column(
        ForeignKey(
            "form_sections.id",
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

    form: Mapped["FormDefinition"] = relationship(
        "FormDefinition",
        lazy="raise",
    )

    section: Mapped["FormSection"] = relationship(
        "FormSection",
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
