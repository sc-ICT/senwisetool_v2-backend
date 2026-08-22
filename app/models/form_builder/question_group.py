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
from app.models.form_builder.enums import QuestionGroupStatus

if TYPE_CHECKING:
    from app.models.form_builder.question_definition import (
        QuestionDefinition,
    )
    from app.models.user import User


class QuestionGroup(Base):
    __tablename__ = "question_groups"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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
        "User",
        foreign_keys=[created_by],
        lazy="raise",
    )

    questions: Mapped[list["QuestionDefinition"]] = relationship(
        "QuestionDefinition",
        secondary="question_group_members",
        back_populates="groups",
        lazy="selectin",
    )

    status: Mapped[QuestionGroupStatus] = mapped_column(
        Enum(
            QuestionGroupStatus,
            name="question_group_status",
        ),
        nullable=False,
        default=QuestionGroupStatus.ACTIVE,
        index=True,
    )
