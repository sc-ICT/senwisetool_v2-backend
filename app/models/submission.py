from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.form_builder.form_definition import FormDefinition
    from app.models.form_builder.project import Project
    from app.models.submission_answer import SubmissionAnswer


class Submission(Base):
    __tablename__ = "submissions"

    __table_args__ = (
        UniqueConstraint(
            "local_id",
            name="uq_submission_local_id",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # ------------------------------------------------------------------
    # Identité locale de l'enquête sur le mobile
    # ------------------------------------------------------------------

    local_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    # ------------------------------------------------------------------
    # Agent ayant effectué la collecte
    # ------------------------------------------------------------------

    agent_id: Mapped[int] = mapped_column(
        ForeignKey(
            "agents.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Projet / formulaire
    # ------------------------------------------------------------------

    project_id: Mapped[int] = mapped_column(
        ForeignKey(
            "projects.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    form_id: Mapped[int] = mapped_column(
        ForeignKey(
            "form_definitions.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    # ------------------------------------------------------------------
    # Snapshot des informations du formulaire
    # ------------------------------------------------------------------

    form_code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    form_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Informations de l'enquête
    # ------------------------------------------------------------------

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="COMPLETED",
        index=True,
    )

    total_questions: Mapped[int] = mapped_column(
        nullable=False,
    )

    answered_questions: Mapped[int] = mapped_column(
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Consentement
    # ------------------------------------------------------------------

    consent_accepted: Mapped[bool] = mapped_column(
        nullable=False,
    )

    consent_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ------------------------------------------------------------------
    # Métadonnées mobiles
    # ------------------------------------------------------------------

    submission_metadata: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )

    # ------------------------------------------------------------------
    # Dates provenant du mobile
    # ------------------------------------------------------------------

    created_at_mobile: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at_mobile: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Date d'enregistrement serveur
    # ------------------------------------------------------------------

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Relations
    # ------------------------------------------------------------------

    agent: Mapped["Agent"] = relationship(
        "Agent",
        lazy="raise",
    )

    project: Mapped["Project"] = relationship(
        "Project",
        lazy="raise",
    )

    form: Mapped["FormDefinition"] = relationship(
        "FormDefinition",
        lazy="raise",
    )

    answers: Mapped[list["SubmissionAnswer"]] = relationship(
        "SubmissionAnswer",
        back_populates="submission",
        cascade="all, delete-orphan",
        order_by="SubmissionAnswer.id",
        lazy="selectin",
    )
