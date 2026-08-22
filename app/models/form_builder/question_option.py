from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
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

if TYPE_CHECKING:
    from app.models.form_builder.question_version import (
        QuestionVersion,
    )


class QuestionOption(Base):
    """
    Option d'une version de question.

    Exemple :

        Question :
            Type de culture

        Options :
            - Cacao
            - Café
            - Hévéa

    Une option appartient toujours à une version précise
    d'une question.
    """

    __tablename__ = "question_options"

    __table_args__ = (
        UniqueConstraint(
            "question_version_id",
            "value",
            name="uq_question_option_value",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    question_version_id: Mapped[int] = mapped_column(
        ForeignKey(
            "question_versions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    value: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    label: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    option_metadata: Mapped[dict] = mapped_column(
        "metadata",
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

    question_version: Mapped["QuestionVersion"] = relationship(
        back_populates="options",
    )
