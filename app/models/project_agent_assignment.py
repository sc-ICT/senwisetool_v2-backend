from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.file_node import FileNode
    from app.models.form_builder.project import Project


class ProjectAgentAssignment(Base):
    __tablename__ = "project_agent_assignments"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "agent_id",
            name="uq_project_agent_assignment",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    project_id: Mapped[int] = mapped_column(
        ForeignKey(
            "projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    agent_id: Mapped[int] = mapped_column(
        ForeignKey(
            "agents.id",
            ondelete="CASCADE",
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

    # ============================================================
    # Relations
    # ============================================================

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="agent_assignments",
        lazy="raise",
    )

    agent: Mapped["Agent"] = relationship(
        "Agent",
        back_populates="project_assignments",
        lazy="raise",
    )

    zones: Mapped[list["ProjectAgentAssignmentZone"]] = relationship(
        "ProjectAgentAssignmentZone",
        back_populates="assignment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ProjectAgentAssignmentZone(Base):
    __tablename__ = "project_agent_assignment_zones"

    __table_args__ = (
        UniqueConstraint(
            "assignment_id",
            "file_node_id",
            name="uq_assignment_zone",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    assignment_id: Mapped[int] = mapped_column(
        ForeignKey(
            "project_agent_assignments.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    file_node_id: Mapped[int] = mapped_column(
        ForeignKey(
            "file_nodes.id",
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

    # ============================================================
    # Relations
    # ============================================================

    assignment: Mapped["ProjectAgentAssignment"] = relationship(
        "ProjectAgentAssignment",
        back_populates="zones",
        lazy="raise",
    )

    file_node: Mapped["FileNode"] = relationship(
        "FileNode",
        lazy="raise",
    )
