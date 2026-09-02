from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database import Base
from app.models.form_builder.enums import (
    QuestionDefinitionStatus,
)
from app.models.form_builder.question_group import (
    QuestionGroup,
)

if TYPE_CHECKING:
    from app.models.form_builder.question_version import QuestionVersion
    from app.models.user import User


class QuestionDefinition(Base):
    """
    Définition principale d'une question dans la banque.

    Cette table représente l'identité réutilisable d'une question.

    Exemple :

        code = "AGE"
        name = "Âge"
        question_type = INTEGER

    Les contraintes propres à un formulaire
    ne sont PAS stockées ici.
    """

    __tablename__ = "question_definitions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    code: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    status: Mapped[QuestionDefinitionStatus] = mapped_column(
        Enum(
            QuestionDefinitionStatus,
            name="question_definition_status",
        ),
        nullable=False,
        default=QuestionDefinitionStatus.ACTIVE,
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

    created_by_user: Mapped["User"] = relationship(
        foreign_keys=[created_by],
        lazy="joined",
    )

    versions: Mapped[list["QuestionVersion"]] = relationship(
        back_populates="question_definition",
        cascade="all, delete-orphan",
        order_by="QuestionVersion.version",
    )

    groups: Mapped[list["QuestionGroup"]] = relationship(
        "QuestionGroup",
        secondary="question_group_members",
        back_populates="questions",
        lazy="selectin",
    )
