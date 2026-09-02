from __future__ import annotations

from datetime import datetime

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


class FormQuestionDependency(Base):
    __tablename__ = "form_question_dependencies"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    target_question_id: Mapped[int] = mapped_column(
        ForeignKey(
            "form_questions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    condition: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )

    actions_if_true: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    actions_if_false: Mapped[list] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    target_question = relationship(
        "FormQuestion",
        foreign_keys=[target_question_id],
    )
