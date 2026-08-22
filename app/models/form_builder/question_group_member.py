from sqlalchemy import (
    ForeignKey,
    Integer,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from app.database import Base


class QuestionGroupMember(Base):
    __tablename__ = "question_group_members"

    question_group_id: Mapped[int] = mapped_column(
        ForeignKey(
            "question_groups.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    question_definition_id: Mapped[int] = mapped_column(
        ForeignKey(
            "question_definitions.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
