from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    DateTime,
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

if TYPE_CHECKING:
    from app.models.form_builder.form_definition import FormDefinition
    from app.models.form_builder.form_question import FormQuestion


class FormSection(Base):
    __tablename__ = "form_sections"

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

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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
        back_populates="sections",
        lazy="raise",
    )

    questions: Mapped[list["FormQuestion"]] = relationship(
        "FormQuestion",
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="FormQuestion.position",
        lazy="selectin",
    )
