from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database import Base
from app.models.form_builder.enums import (
    QuestionType,
)

if TYPE_CHECKING:
    from app.models.form_builder.question_definition import (
        QuestionDefinition,
    )
    from app.models.form_builder.question_option import (
        QuestionOption,
    )


class QuestionVersion(Base):
    """
    Version d'une question de la banque.

    Une QuestionDefinition représente l'identité
    d'une question.

    Une QuestionVersion représente une définition
    précise de cette question.

    Exemple :

        AGE
        ├── v1
        ├── v2
        └── v3
    """

    __tablename__ = "question_versions"

    __table_args__ = (
        UniqueConstraint(
            "question_definition_id",
            "version",
            name="uq_question_version",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    question_definition_id: Mapped[int] = mapped_column(
        ForeignKey(
            "question_definitions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    label: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    help_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    question_type: Mapped[QuestionType] = mapped_column(
        Enum(
            QuestionType,
            name="question_type",
        ),
        nullable=False,
    )

    base_config: Mapped[dict] = mapped_column(
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

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    question_definition: Mapped["QuestionDefinition"] = relationship(
        back_populates="versions",
    )

    options: Mapped[list["QuestionOption"]] = relationship(
        back_populates="question_version",
        cascade="all, delete-orphan",
        order_by="QuestionOption.position",
    )
