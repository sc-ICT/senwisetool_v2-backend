from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import UserRole, UserStatus

if TYPE_CHECKING:
    from app.models.file_node import FileNode

# if TYPE_CHECKING:
#     from app.models.deployment import AgentForm


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.USER, nullable=False
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"), default=UserStatus.PENDING, nullable=False
    )

    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    email_verification_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_verification_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    refresh_token: Mapped[str | None] = mapped_column(String(512), nullable=True)
    refresh_token_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reset_password_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_password_expires: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    file_nodes: Mapped[list["FileNode"]] = relationship(
        "FileNode",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # Relations — TYPE_CHECKING évite l'import circulaire
    # SQLAlchemy résout les strings automatiquement au runtime
    # mobile_agents: Mapped[list[UserMobile]] = relationship(
    #     "UserMobile", back_populates="user", cascade="all, delete-orphan"
    # )
    # question_domains: Mapped[list[QuestionDomain]] = relationship(
    #     "QuestionDomain", back_populates="user", cascade="all, delete-orphan"
    # )
    # questions: Mapped[list[Question]] = relationship(
    #     "Question", back_populates="user", cascade="all, delete-orphan"
    # )
    # forms: Mapped[list[Form]] = relationship(
    #     "Form", back_populates="user", cascade="all, delete-orphan"
    # )


# class UserMobile(Base):
#     __tablename__ = "user_mobiles"

#     id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
#     agent_name: Mapped[str] = mapped_column(String(255), nullable=False)
#     token: Mapped[str] = mapped_column(String(512), unique=True, nullable=False, index=True)
#     status: Mapped[UserStatus] = mapped_column(
#         Enum(UserStatus, name="user_status"), default=UserStatus.ACTIVE, nullable=False
#     )

#     user_id: Mapped[int] = mapped_column(
#         Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
#     )

#     created_at: Mapped[datetime] = mapped_column(
#         DateTime(timezone=True), server_default=func.now(), nullable=False
#     )
#     updated_at: Mapped[datetime] = mapped_column(
#         DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
#     )

#     user: Mapped[User] = relationship("User", back_populates="mobile_agents")
#     agent_forms: Mapped[list[AgentForm]] = relationship(
#         "AgentForm", back_populates="user_mobile", cascade="all, delete-orphan"
#     )
