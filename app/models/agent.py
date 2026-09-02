from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import AgentRole, AgentStatus

if TYPE_CHECKING:
    from app.models.user import User


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    role: Mapped[AgentRole] = mapped_column(
        Enum(
            AgentRole,
            name="agent_role",
        ),
        nullable=False,
        index=True,
    )

    status: Mapped[AgentStatus] = mapped_column(
        Enum(
            AgentStatus,
            name="agent_status",
        ),
        nullable=False,
        default=AgentStatus.ACTIVE,
        index=True,
    )

    token: Mapped[str] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
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

    user: Mapped["User"] = relationship(
        "User",
        back_populates="agents",
        lazy="raise",
    )
