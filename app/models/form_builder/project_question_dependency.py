from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database import Base


class ProjectQuestionDependency(Base):
    __tablename__ = "project_question_dependencies"

    __table_args__ = (
        UniqueConstraint(
            "target_question_id",
            "source_question_id",
            name="uq_project_question_dependency_pair",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    target_question_id: Mapped[int] = mapped_column(
        ForeignKey(
            "project_questions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    source_question_id: Mapped[int] = mapped_column(
        ForeignKey(
            "project_questions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    operator: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    value: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    target_question = relationship(
        "ProjectQuestion",
        foreign_keys=[target_question_id],
    )

    source_question = relationship(
        "ProjectQuestion",
        foreign_keys=[source_question_id],
    )
