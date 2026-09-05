from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.submission import Submission


class SubmissionAnswer(Base):
    __tablename__ = "submission_answers"

    __table_args__ = (
        UniqueConstraint(
            "submission_id",
            "question_id",
            name="uq_submission_answer_question",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    submission_id: Mapped[int] = mapped_column(
        ForeignKey(
            "submissions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Question
    # ------------------------------------------------------------------

    question_id: Mapped[int] = mapped_column(
        nullable=False,
        index=True,
    )

    question_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Valeur de la réponse
    # ------------------------------------------------------------------

    value: Mapped[object] = mapped_column(
        JSON,
        nullable=True,
    )

    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relation
    # ------------------------------------------------------------------

    submission: Mapped["Submission"] = relationship(
        "Submission",
        back_populates="answers",
        lazy="raise",
    )
